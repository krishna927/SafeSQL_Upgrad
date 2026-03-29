"""Data loader for WikiSQL_VALUE dataset.

WikiSQL_VALUE is a dialectal variant dataset with:
- Standard splits: train, dev, test
- 6 dialectal variants: AppE, ChcE, CollSgE, IndE, MULTI, UAAVE
- Single-table queries with structured SQL representation
- SQLite databases and table schemas in JSONL format
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from .base_loader import BaseDatasetLoader

logger = logging.getLogger(__name__)


class WikiSQLValueLoader(BaseDatasetLoader):
    """Loader for WikiSQL_VALUE dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize WikiSQL_VALUE loader.
        
        Args:
            data_dir: Path to WikiSQL_VALUE extracted data directory.
                     Defaults to safesql/data/datasets/wikisql_value/extracted/data
        """
        if data_dir is None:
            # Default to project data directory
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "wikisql_value" / "extracted" / "data"
        
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"WikiSQL_VALUE data directory not found: {self.data_dir}")
        
        # Cache for loaded data
        self._tables_cache: Dict[str, Dict] = {}
        self._queries_cache: Dict[str, List[Dict]] = {}
        
        logger.info(f"Initialized WikiSQL_VALUE loader with data_dir: {self.data_dir}")
    
    def load_tables(self, split: str = "dev") -> Dict[str, Dict]:
        """
        Load table schemas from tables.jsonl file.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            
        Returns:
            Dictionary mapping table_id to table schema
        """
        if split in self._tables_cache:
            return self._tables_cache[split]
        
        tables_file = self.data_dir / f"{split}.tables.jsonl"
        if not tables_file.exists():
            raise FileNotFoundError(f"Tables file not found: {tables_file}")
        
        tables = {}
        with open(tables_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    table_data = json.loads(line.strip())
                    table_id = table_data.get('id')
                    if table_id:
                        tables[table_id] = table_data
        
        self._tables_cache[split] = tables
        logger.info(f"Loaded {len(tables)} tables from {split} split")
        return tables
    
    def load_queries(self, split: str = "dev", dialect: Optional[str] = None) -> List[Dict]:
        """
        Load queries from JSONL file.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            dialect: Dialectal variant (None for standard, or 'AppE', 'ChcE', etc.)
            
        Returns:
            List of query dictionaries
        """
        cache_key = f"{split}_{dialect or 'standard'}"
        if cache_key in self._queries_cache:
            return self._queries_cache[cache_key]
        
        if dialect:
            queries_file = self.data_dir / f"{split}_{dialect}.jsonl"
        else:
            queries_file = self.data_dir / f"{split}.jsonl"
        
        if not queries_file.exists():
            raise FileNotFoundError(f"Queries file not found: {queries_file}")
        
        queries = []
        with open(queries_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        query_data = json.loads(line.strip())
                        # Add metadata
                        query_data['_line_number'] = line_num
                        query_data['_split'] = split
                        query_data['_dialect'] = dialect or 'standard'
                        queries.append(query_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing line {line_num} in {queries_file}: {e}")
        
        self._queries_cache[cache_key] = queries
        logger.info(f"Loaded {len(queries)} queries from {queries_file.name}")
        return queries
    
    def get_table_schema(self, table_id: str, split: str = "dev") -> Optional[Dict]:
        """
        Get schema for a specific table.
        
        Args:
            table_id: Table identifier (e.g., "1-10015132-11")
            split: Dataset split to load tables from
            
        Returns:
            Table schema dictionary or None if not found
        """
        tables = self.load_tables(split)
        return tables.get(table_id)
    
    def get_database_path(self, db_id: str = None, split: str = "dev") -> Optional[Path]:
        """
        Get path to database file (WikiSQL uses a single database per split).
        
        Args:
            db_id: Table identifier (ignored for WikiSQL, kept for compatibility)
            split: Dataset split
            
        Returns:
            Path to database file
        """
        db_file = self.data_dir / f"{split}.db"
        if db_file.exists():
            return db_file
        return None
    
    def get_database_connection(self, split_or_db_id: str = "dev") -> sqlite3.Connection:
        """
        Get SQLite database connection for executing queries.
        
        WikiSQL_VALUE uses a single database file per split (dev.db, train.db, test.db).
        The parameter can be either a split name ("dev", "train", "test") or a table_id
        (in which case we use "dev" as default).
        
        Args:
            split_or_db_id: Dataset split ("dev", "train", "test") or table_id (ignored)
            
        Returns:
            SQLite connection object
        """
        # If it's a known split, use it; otherwise default to "dev"
        if split_or_db_id in ["dev", "train", "test"]:
            split = split_or_db_id
        else:
            # Assume it's a table_id and use "dev" split
            split = "dev"
        
        db_file = self.data_dir / f"{split}.db"
        if not db_file.exists():
            raise FileNotFoundError(f"Database file not found: {db_file}")
        
        conn = sqlite3.connect(str(db_file))
        return conn
    
    def convert_sql_to_string(self, sql_dict: Dict, table_schema: Dict) -> str:
        """
        Convert WikiSQL structured SQL format to SQL string.
        
        WikiSQL format:
        {
            "sel": column_index,      # Selected column index
            "conds": [[col_idx, op_idx, value], ...],  # Conditions
            "agg": agg_type            # Aggregation type (0=None, 1=MAX, 2=MIN, 3=COUNT, 4=SUM, 5=AVG)
        }
        
        Args:
            sql_dict: SQL in WikiSQL format
            table_schema: Table schema dictionary with 'header' field
            
        Returns:
            SQL query string
        """
        from ...utils.sql_identifier import quote_identifier
        
        header = table_schema.get('header', [])
        table_name = table_schema.get('name', 'table')
        
        # Aggregation types
        agg_types = {
            0: '',      # No aggregation
            1: 'MAX',
            2: 'MIN',
            3: 'COUNT',
            4: 'SUM',
            5: 'AVG'
        }
        
        # Operator types
        operators = {
            0: '=',    # Equal
            1: '>',    # Greater than
            2: '<',    # Less than
            3: '!='    # Not equal
        }
        
        # Get selected column
        # WikiSQL_VALUE uses generic column names (col0, col1, etc.) in database
        sel_idx = sql_dict.get('sel', 0)
        if sel_idx >= len(header):
            raise ValueError(f"Column index {sel_idx} out of range for table with {len(header)} columns")
        
        # Use generic column name (col0, col1, etc.) for database compatibility
        selected_col = f"col{sel_idx}"
        quoted_selected_col = quote_identifier(selected_col)
        
        # Build SELECT clause
        agg_type = sql_dict.get('agg', 0)
        if agg_type == 0:
            select_clause = f"SELECT {quoted_selected_col}"
        else:
            agg_func = agg_types.get(agg_type, '')
            select_clause = f"SELECT {agg_func}({quoted_selected_col})"
        
        # Build FROM clause - quote table name if needed
        quoted_table_name = quote_identifier(table_name)
        from_clause = f"FROM {quoted_table_name}"
        
        # Build WHERE clause
        conds = sql_dict.get('conds', [])
        where_parts = []
        for cond in conds:
            if len(cond) >= 3:
                col_idx, op_idx, value = cond[0], cond[1], cond[2]
                if col_idx < len(header):
                    # Use generic column name (col0, col1, etc.) for database compatibility
                    col_name = f"col{col_idx}"
                    quoted_col_name = quote_identifier(col_name)
                    op = operators.get(op_idx, '=')
                    # Escape string values
                    if isinstance(value, str):
                        escaped_value = value.replace("'", "''")
                        value = f"'{escaped_value}'"
                    where_parts.append(f"{quoted_col_name} {op} {value}")
        
        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)
        
        # Combine into SQL string
        sql_string = f"{select_clause} {from_clause}"
        if where_clause:
            sql_string += f" {where_clause}"
        
        return sql_string
    
    def get_dataset_name(self) -> str:
        """Get dataset name."""
        return "wikisql_value"
    
    def get_query_with_schema(self, query_dict: Dict, split: str = "dev") -> Dict:
        """
        Get query with its associated table schema.
        
        Args:
            query_dict: Query dictionary from load_queries()
            split: Dataset split
            
        Returns:
            Dictionary with query and schema information
        """
        table_id = query_dict.get('table_id')
        if not table_id:
            raise ValueError("Query missing table_id")
        
        table_schema = self.get_table_schema(table_id, split)
        if not table_schema:
            raise ValueError(f"Table schema not found for table_id: {table_id}")
        
        # Create a copy to avoid modifying cached schema
        table_schema = table_schema.copy()
        
        # Fix table name: WikiSQL_VALUE database uses 'table_1_' prefix
        # Schema has 'table_XXX' but database has 'table_1_XXX'
        schema_table_name = table_schema.get('name', '')
        if schema_table_name.startswith('table_') and not schema_table_name.startswith('table_1_'):
            # Add '1_' prefix after 'table_'
            actual_table_name = 'table_1_' + schema_table_name[6:]  # Remove 'table_' and add 'table_1_'
            table_schema['name'] = actual_table_name
        
        # Add database column names (col0, col1, etc.) to schema
        # WikiSQL_VALUE database uses generic column names
        table_schema['database_name'] = 'wikisql_value'
        if 'header' in table_schema:
            columns = []
            for i, header_name in enumerate(table_schema['header']):
                col_info = {
                    'name': header_name,  # Human-readable name
                    'db_name': f'col{i}',  # Database column name
                    'index': i,
                    'type': table_schema.get('types', ['text'] * len(table_schema['header']))[i] if 'types' in table_schema else 'text'
                }
                columns.append(col_info)
            table_schema['columns'] = columns
        
        # Convert SQL to string format
        sql_string = None
        if query_dict.get('sql'):
            try:
                sql_string = self.convert_sql_to_string(query_dict['sql'], table_schema)
            except Exception as e:
                logger.warning(f"Error converting SQL to string: {e}")
        
        return {
            'query': query_dict,
            'table_schema': table_schema,
            'sql_string': sql_string,
            'table_id': table_id
        }
    
    def get_sample(self, split: str = "dev", n: int = 5, dialect: Optional[str] = None, **kwargs) -> List[Dict]:
        """
        Get a sample of queries with their schemas.
        
        Args:
            split: Dataset split
            n: Number of samples to return
            dialect: Dialectal variant (None for standard)
            
        Returns:
            List of query dictionaries with schema information
        """
        queries = self.load_queries(split, dialect)
        samples = []
        
        for query in queries[:n]:
            try:
                query_with_schema = self.get_query_with_schema(query, split)
                samples.append(query_with_schema)
            except Exception as e:
                logger.warning(f"Error processing query: {e}")
                continue
        
        return samples


if __name__ == "__main__":
    # Test the loader
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    loader = WikiSQLValueLoader()
    
    # Test loading tables
    print("=" * 60)
    print("Testing WikiSQL_VALUE Loader")
    print("=" * 60)
    
    # Load tables
    tables = loader.load_tables("dev")
    print(f"\nLoaded {len(tables)} tables")
    if tables:
        first_table_id = list(tables.keys())[0]
        print(f"\nFirst table ID: {first_table_id}")
        print(f"Columns: {tables[first_table_id].get('header', [])}")
    
    # Load queries
    queries = loader.load_queries("dev", dialect=None)
    print(f"\nLoaded {len(queries)} queries from dev split")
    
    # Get sample with schemas
    print("\n" + "=" * 60)
    print("Sample Queries with Schemas")
    print("=" * 60)
    samples = loader.get_sample("dev", n=3)
    
    for i, sample in enumerate(samples, 1):
        print(f"\n--- Sample {i} ---")
        print(f"Question: {sample['query']['question']}")
        print(f"Table ID: {sample['table_id']}")
        print(f"Table Name: {sample['table_schema'].get('name', 'N/A')}")
        print(f"Columns: {sample['table_schema'].get('header', [])}")
        print(f"SQL (structured): {sample['query']['sql']}")
        if sample['sql_string']:
            print(f"SQL (string): {sample['sql_string']}")
