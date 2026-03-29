"""Data loader for BIRD dataset.

BIRD Dataset:
- Format: JSON files (train.json, dev.json)
- Databases: SQLite files in dev_databases/ directory
- Schemas: Extracted from database files
- SQL Format: SQL strings
- Multi-table queries with joins, subqueries, aggregations
- Includes external knowledge requirements (evidence field)
- Real-world dirty databases with complex schemas
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import random

from .base_loader import BaseDatasetLoader

logger = logging.getLogger(__name__)


class BIRDLoader(BaseDatasetLoader):
    """Loader for BIRD dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize BIRD dataset loader.
        
        Args:
            data_dir: Path to BIRD dataset directory.
                     Expected structure:
                     bird/
                     ├── train/
                     │   └── train.json
                     ├── dev/
                     │   └── dev.json
                     └── dev_databases/
                         ├── database_1/
                         │   └── database_1.sqlite
                         └── ...
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "bird"
        
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"BIRD data directory not found: {self.data_dir}")
        
        self.database_dir = self.data_dir / "dev_databases"
        self.train_file = self.data_dir / "train" / "train.json"
        self.dev_file = self.data_dir / "dev" / "dev.json"
        
        # Cache for loaded data
        self._queries_cache: Dict[str, List[Dict]] = {}
        self._schemas_cache: Dict[str, Dict] = {}
        
        logger.info(f"Initialized BIRD loader with data_dir: {self.data_dir}")
    
    def load_queries(self, split: str = "dev", **kwargs) -> List[Dict]:
        """
        Load queries from BIRD JSON file.
        
        Args:
            split: Dataset split ('train', 'dev')
            **kwargs: Additional parameters (ignored for BIRD)
            
        Returns:
            List of query dictionaries
        """
        cache_key = split
        if cache_key in self._queries_cache:
            return self._queries_cache[cache_key]
        
        # Map split to filename
        if split == "train":
            queries_file = self.train_file
        elif split == "dev":
            queries_file = self.dev_file
        elif split == "test":
            # BIRD test set may require evaluation server
            queries_file = self.data_dir / "test" / "test.json"
        else:
            raise ValueError(f"Unknown split: {split}")
        
        if not queries_file.exists():
            raise FileNotFoundError(f"Queries file not found: {queries_file}")
        
        queries = []
        with open(queries_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for query_data in data:
                # Add metadata
                query_data['_split'] = split
                query_data['_dataset'] = 'bird'
                queries.append(query_data)
        
        self._queries_cache[cache_key] = queries
        logger.info(f"Loaded {len(queries)} queries from {queries_file.name}")
        return queries
    
    def load_tables(self) -> Dict[str, Dict]:
        """
        Load all database schemas by introspecting database files.
        
        BIRD doesn't have a tables.json file like Spider, so we extract
        schemas directly from database files.
        
        Returns:
            Dictionary mapping db_id to schema dictionary
        """
        if self._schemas_cache:
            return self._schemas_cache
        
        schemas = {}
        
        if not self.database_dir.exists():
            logger.warning(f"Database directory not found: {self.database_dir}")
            return schemas
        
        # Iterate through database directories
        for db_dir in self.database_dir.iterdir():
            if not db_dir.is_dir():
                continue
            
            db_id = db_dir.name
            
            # Find SQLite file in directory
            sqlite_files = list(db_dir.glob("*.sqlite")) + list(db_dir.glob("*.db"))
            if not sqlite_files:
                logger.warning(f"No SQLite file found in {db_dir}")
                continue
            
            db_path = sqlite_files[0]
            
            # Extract schema from database
            schema = self._extract_schema_from_database(db_id, db_path)
            if schema:
                schemas[db_id] = schema
        
        self._schemas_cache = schemas
        logger.info(f"Loaded {len(schemas)} database schemas")
        return schemas
    
    def _extract_schema_from_database(self, db_id: str, db_path: Path) -> Optional[Dict]:
        """
        Extract schema from a SQLite database file.
        
        Args:
            db_id: Database identifier
            db_path: Path to SQLite database file
            
        Returns:
            Database schema dictionary in Spider-compatible format
        """
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            table_names = []
            table_names_original = []
            column_names = [[-1, "*"]]  # Start with special marker
            column_names_original = [[-1, "*"]]
            column_types = []
            foreign_keys = []
            primary_keys = []
            
            col_idx = 1  # Start from 1 (0 is reserved for *)
            
            for table_idx, table_name in enumerate(tables):
                table_names.append(table_name)
                table_names_original.append(table_name)
                
                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name})")
                table_info = cursor.fetchall()
                
                for col_info in table_info:
                    col_id, col_name, col_type, not_null, default_val, pk = col_info
                    
                    column_names.append([table_idx, col_name])
                    column_names_original.append([table_idx, col_name])
                    
                    # Normalize type
                    normalized_type = self._normalize_type(col_type)
                    column_types.append(normalized_type)
                    
                    if pk:
                        primary_keys.append(col_idx)
                    
                    col_idx += 1
                
                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fk_info = cursor.fetchall()
                
                for fk in fk_info:
                    # fk: (id, seq, table, from, to, on_update, on_delete, match)
                    from_col = fk[3]
                    to_table = fk[2]
                    to_col = fk[4]
                    
                    # Find column indices
                    from_col_idx = None
                    to_col_idx = None
                    
                    for idx, (t_idx, c_name) in enumerate(column_names):
                        if t_idx == table_idx and c_name == from_col:
                            from_col_idx = idx
                        if to_table in tables:
                            to_table_idx = tables.index(to_table)
                            if t_idx == to_table_idx and c_name == to_col:
                                to_col_idx = idx
                    
                    if from_col_idx and to_col_idx:
                        foreign_keys.append([from_col_idx, to_col_idx])
            
            conn.close()
            
            # Build schema dictionary in Spider-compatible format
            schema = {
                "db_id": db_id,
                "table_names": table_names,
                "table_names_original": table_names_original,
                "column_names": column_names,
                "column_names_original": column_names_original,
                "column_types": column_types,
                "foreign_keys": foreign_keys,
                "primary_keys": primary_keys
            }
            
            return schema
            
        except Exception as e:
            logger.error(f"Error extracting schema from {db_id}: {e}")
            return None
    
    def _normalize_type(self, col_type: str) -> str:
        """Normalize column type to standard SQL types."""
        col_type_upper = col_type.upper().strip()
        
        type_mapping = {
            'TEXT': 'text',
            'VARCHAR': 'text',
            'CHAR': 'text',
            'STRING': 'text',
            'INTEGER': 'number',
            'INT': 'number',
            'BIGINT': 'number',
            'REAL': 'number',
            'FLOAT': 'number',
            'DOUBLE': 'number',
            'NUMERIC': 'number',
            'BOOLEAN': 'number',
            'BOOL': 'number',
            'DATE': 'text',
            'DATETIME': 'text',
            'TIMESTAMP': 'text',
            'BLOB': 'text'
        }
        
        return type_mapping.get(col_type_upper, 'text')
    
    def get_table_schema(self, db_id: str, split: str = "dev") -> Optional[Dict]:
        """
        Get schema for a specific database.
        
        Args:
            db_id: Database identifier (e.g., "database_1")
            split: Dataset split (not used for BIRD, but kept for interface compatibility)
            
        Returns:
            Database schema dictionary or None if not found
        """
        tables = self.load_tables()
        return tables.get(db_id)
    
    def get_sample(self, split: str = "dev", n: int = 10, **kwargs) -> List[Dict]:
        """
        Get a sample of queries with their schemas.
        
        Args:
            split: Dataset split
            n: Number of samples to return
            **kwargs: Additional parameters
            
        Returns:
            List of dictionaries with query and schema information
        """
        queries = self.load_queries(split)
        tables = self.load_tables()
        
        # Sample queries
        if n > len(queries):
            n = len(queries)
        
        sampled_queries = random.sample(queries, n) if n < len(queries) else queries
        
        samples = []
        for query_data in sampled_queries:
            db_id = query_data.get('db_id')
            if not db_id:
                logger.warning(f"Query missing db_id: {query_data.get('question', 'Unknown')}")
                continue
            
            schema = tables.get(db_id)
            if not schema:
                logger.warning(f"Schema not found for db_id: {db_id}")
                continue
            
            # Format sample similar to Spider format for compatibility
            sample = {
                'query': {
                    'question': query_data.get('question', ''),
                    'sql': query_data.get('SQL', query_data.get('sql', '')),  # BIRD uses 'SQL' field
                    'query': query_data.get('SQL', query_data.get('sql', query_data.get('query', '')))
                },
                'db_id': db_id,
                'table_id': db_id,  # For compatibility
                'database_schema': schema,  # Full database schema
                'table_schema': schema,  # For compatibility
                '_dataset': 'bird',
                '_split': split,
                'evidence': query_data.get('evidence', []),  # BIRD-specific: external knowledge
                'difficulty': query_data.get('difficulty', 'medium')  # BIRD-specific: difficulty level
            }
            samples.append(sample)
        
        logger.info(f"Prepared {len(samples)} samples from BIRD {split} split")
        return samples
    
    def convert_sql_to_string(self, sql: Any, schema: Dict) -> str:
        """
        Convert BIRD SQL to string format.
        
        BIRD provides SQL as strings, so this is mostly a pass-through,
        but we ensure proper formatting and identifier quoting.
        
        Args:
            sql: SQL string (BIRD format)
            schema: Database schema dictionary
            
        Returns:
            SQL query string
        """
        from ...utils.sql_identifier import quote_identifier, needs_quoting
        
        if isinstance(sql, dict):
            # If somehow we get a dict, try to extract SQL
            sql = sql.get('SQL', sql.get('sql', sql.get('query', '')))
        
        if not isinstance(sql, str):
            sql = str(sql)
        
        # BIRD SQL is already a string, return as-is
        return sql.strip()
    
    def get_database_path(self, db_id: str, split: str = "dev") -> Optional[Path]:
        """
        Get path to database SQLite file.
        
        Args:
            db_id: Database identifier (e.g., "database_1")
            split: Dataset split (not used for BIRD)
            
        Returns:
            Path to database file or None if not found
        """
        db_dir = self.database_dir / db_id
        
        if not db_dir.exists():
            logger.warning(f"Database directory not found: {db_dir}")
            return None
        
        # Find SQLite file in directory
        sqlite_files = list(db_dir.glob("*.sqlite")) + list(db_dir.glob("*.db"))
        
        if sqlite_files:
            return sqlite_files[0]
        
        logger.warning(f"Database file not found for db_id: {db_id}")
        return None
    
    def get_database_connection(self, db_id: str) -> Optional[sqlite3.Connection]:
        """
        Get SQLite database connection for a database.
        
        Args:
            db_id: Database identifier
            
        Returns:
            SQLite connection or None if database not found
        """
        db_path = self.get_database_path(db_id)
        if not db_path:
            return None
        
        try:
            conn = sqlite3.connect(str(db_path))
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database {db_id}: {e}")
            return None
    
    def get_dataset_name(self) -> str:
        """Get dataset name."""
        return "bird"


if __name__ == "__main__":
    # Test the loader
    import sys
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("Testing BIRD Dataset Loader")
    print("=" * 60)
    
    try:
        loader = BIRDLoader()
        
        # Load queries
        print("\nLoading dev queries...")
        queries = loader.load_queries("dev")
        print(f"Loaded {len(queries)} queries")
        
        if queries:
            print(f"\nFirst query:")
            first_query = queries[0]
            print(f"  Question: {first_query.get('question', 'N/A')[:80]}")
            print(f"  DB ID: {first_query.get('db_id', 'N/A')}")
            print(f"  SQL: {first_query.get('SQL', first_query.get('sql', 'N/A'))[:100]}")
            print(f"  Evidence: {first_query.get('evidence', [])}")
            print(f"  Difficulty: {first_query.get('difficulty', 'N/A')}")
        
        # Load tables
        print("\nLoading database schemas...")
        tables = loader.load_tables()
        print(f"Loaded {len(tables)} database schemas")
        
        if tables:
            first_db_id = list(tables.keys())[0]
            print(f"\nFirst database: {first_db_id}")
            schema = tables[first_db_id]
            print(f"  Tables: {schema.get('table_names', [])}")
            print(f"  Columns: {len(schema.get('column_names', []))} columns")
        
        # Get sample
        print("\nGetting sample...")
        samples = loader.get_sample("dev", n=3)
        print(f"Got {len(samples)} samples")
        
        for i, sample in enumerate(samples, 1):
            print(f"\n--- Sample {i} ---")
            print(f"Question: {sample['query']['question'][:60]}...")
            print(f"DB ID: {sample['db_id']}")
            print(f"SQL: {sample['query']['sql'][:80]}...")
            print(f"Evidence: {sample.get('evidence', [])}")
            print(f"Difficulty: {sample.get('difficulty', 'N/A')}")
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease ensure BIRD dataset is downloaded to:")
        print("  safesql/data/datasets/bird/")
        print("\nExpected structure:")
        print("  bird/")
        print("  ├── train/")
        print("  │   └── train.json")
        print("  ├── dev/")
        print("  │   └── dev.json")
        print("  └── dev_databases/")
        print("      ├── database_1/")
        print("      │   └── database_1.sqlite")
        print("      └── ...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
