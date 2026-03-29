"""Data loader for Spider dataset.

Spider Dataset:
- Format: JSON files (train_spider.json, dev.json)
- Databases: SQLite files in database/ directory
- Schemas: tables.json (all schemas)
- SQL Format: SQL strings (not structured)
- Multi-table queries with joins, subqueries, aggregations
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import random

from .base_loader import BaseDatasetLoader

logger = logging.getLogger(__name__)


class SpiderLoader(BaseDatasetLoader):
    """Loader for Spider dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize Spider dataset loader.
        
        Args:
            data_dir: Path to Spider dataset directory.
                     Expected structure:
                     spider/
                     ├── train_spider.json
                     ├── dev.json
                     ├── tables.json
                     └── database/
                         ├── academic/
                         │   └── academic.sqlite
                         └── ...
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "spider"
        
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Spider data directory not found: {self.data_dir}")
        
        self.database_dir = self.data_dir / "database"
        self.tables_file = self.data_dir / "tables.json"
        
        # Cache for loaded data
        self._tables_cache: Dict[str, Dict] = {}
        self._queries_cache: Dict[str, List[Dict]] = {}
        self._schemas_cache: Dict[str, Dict] = {}
        
        logger.info(f"Initialized Spider loader with data_dir: {self.data_dir}")
    
    def load_queries(self, split: str = "dev", **kwargs) -> List[Dict]:
        """
        Load queries from Spider JSON file.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            **kwargs: Additional parameters (ignored for Spider)
            
        Returns:
            List of query dictionaries
        """
        cache_key = split
        if cache_key in self._queries_cache:
            return self._queries_cache[cache_key]
        
        # Map split to filename
        if split == "train":
            queries_file = self.data_dir / "train_spider.json"
        elif split == "dev":
            queries_file = self.data_dir / "dev.json"
        elif split == "test":
            # Test set may not be available (requires evaluation server)
            queries_file = self.data_dir / "test.json"
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
                query_data['_dataset'] = 'spider'
                queries.append(query_data)
        
        self._queries_cache[cache_key] = queries
        logger.info(f"Loaded {len(queries)} queries from {queries_file.name}")
        return queries
    
    def load_tables(self) -> Dict[str, Dict]:
        """
        Load all table schemas from tables.json.
        
        Returns:
            Dictionary mapping db_id to schema dictionary
        """
        if self._tables_cache:
            return self._tables_cache
        
        if not self.tables_file.exists():
            raise FileNotFoundError(f"Tables file not found: {self.tables_file}")
        
        with open(self.tables_file, 'r', encoding='utf-8') as f:
            tables_data = json.load(f)
        
        # Convert list to dict keyed by db_id
        tables = {}
        for table_info in tables_data:
            db_id = table_info.get('db_id')
            if db_id:
                tables[db_id] = table_info
        
        self._tables_cache = tables
        logger.info(f"Loaded {len(tables)} database schemas")
        return tables
    
    def get_table_schema(self, db_id: str, split: str = "dev") -> Optional[Dict]:
        """
        Get schema for a specific database.
        
        Args:
            db_id: Database identifier (e.g., "academic")
            split: Dataset split (not used for Spider, but kept for interface compatibility)
            
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
            
            # Format sample similar to WikiSQL format for compatibility
            sample = {
                'query': {
                    'question': query_data.get('question', ''),
                    'sql': query_data.get('sql', ''),  # Spider provides SQL string
                    'query': query_data.get('query', query_data.get('sql', ''))
                },
                'db_id': db_id,
                'table_id': db_id,  # For compatibility
                'database_schema': schema,  # Full database schema
                'table_schema': schema,  # For compatibility with WikiSQL interface
                '_dataset': 'spider',
                '_split': split
            }
            samples.append(sample)
        
        logger.info(f"Prepared {len(samples)} samples from Spider {split} split")
        return samples
    
    def convert_sql_to_string(self, sql: Any, schema: Dict) -> str:
        """
        Convert Spider SQL to string format.
        
        Spider provides SQL as strings, so this is mostly a pass-through,
        but we ensure proper formatting and identifier quoting.
        
        Args:
            sql: SQL string (Spider format)
            schema: Database schema dictionary
            
        Returns:
            SQL query string
        """
        from ...utils.sql_identifier import quote_identifier, needs_quoting
        
        if isinstance(sql, dict):
            # If somehow we get a dict, try to extract SQL
            sql = sql.get('sql', sql.get('query', ''))
        
        if not isinstance(sql, str):
            sql = str(sql)
        
        # Spider SQL is already a string, but we may need to quote identifiers
        # For now, return as-is (identifier quoting handled in generator)
        return sql.strip()
    
    def get_database_path(self, db_id: str, split: str = "dev") -> Optional[Path]:
        """
        Get path to database SQLite file.
        
        Args:
            db_id: Database identifier (e.g., "academic")
            split: Dataset split (not used for Spider)
            
        Returns:
            Path to database file or None if not found
        """
        db_path = self.database_dir / db_id / f"{db_id}.sqlite"
        
        # Try alternative naming conventions
        if not db_path.exists():
            # Some databases might be named differently
            db_path = self.database_dir / db_id / f"{db_id}.db"
        
        if not db_path.exists():
            # Check if database directory exists
            db_dir = self.database_dir / db_id
            if db_dir.exists():
                # Find any .sqlite or .db file in the directory
                sqlite_files = list(db_dir.glob("*.sqlite")) + list(db_dir.glob("*.db"))
                if sqlite_files:
                    db_path = sqlite_files[0]
        
        if db_path.exists():
            return db_path
        
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
        return "spider"


if __name__ == "__main__":
    # Test the loader
    import sys
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("Testing Spider Dataset Loader")
    print("=" * 60)
    
    try:
        loader = SpiderLoader()
        
        # Load queries
        print("\nLoading dev queries...")
        queries = loader.load_queries("dev")
        print(f"Loaded {len(queries)} queries")
        
        if queries:
            print(f"\nFirst query:")
            first_query = queries[0]
            print(f"  Question: {first_query.get('question', 'N/A')[:80]}")
            print(f"  DB ID: {first_query.get('db_id', 'N/A')}")
            print(f"  SQL: {first_query.get('sql', 'N/A')[:100]}")
        
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
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease ensure Spider dataset is downloaded to:")
        print("  safesql/data/datasets/spider/")
        print("\nExpected structure:")
        print("  spider/")
        print("  ├── dev.json")
        print("  ├── train_spider.json")
        print("  ├── tables.json")
        print("  └── database/")
        print("      ├── academic/")
        print("      │   └── academic.sqlite")
        print("      └── ...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
