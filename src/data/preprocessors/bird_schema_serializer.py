"""Schema extraction and serialization for BIRD dataset.

BIRD dataset has multi-table databases similar to Spider, but with:
- Real-world dirty databases
- External knowledge requirements (evidence field)
- More complex schemas
- Database schemas extracted directly from SQLite files (no tables.json)
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BIRDSchemaSerializer:
    """Extract and serialize schemas from BIRD dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize BIRD schema serializer.
        
        Args:
            data_dir: Path to BIRD dataset directory
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "bird"
        
        self.data_dir = Path(data_dir)
        self.database_dir = self.data_dir / "dev_databases"
        logger.info(f"Initialized BIRD schema serializer with data_dir: {self.data_dir}")
    
    def extract_schema_from_database_info(self, db_info: Dict) -> Dict:
        """
        Extract schema from BIRD database info dictionary.
        
        BIRD format is similar to Spider:
        {
            "db_id": "database_1",
            "table_names": ["table1", "table2"],
            "table_names_original": ["table1", "table2"],
            "column_names": [[-1, "*"], [0, "col1"], [0, "col2"], [1, "col3"]],
            "column_names_original": [[-1, "*"], [0, "col1"], [0, "col2"], [1, "col3"]],
            "column_types": ["text", "text", "text", "text"],
            "foreign_keys": [[1, 2]],
            "primary_keys": [0, 3]
        }
        
        Args:
            db_info: Database info dictionary (from loader)
            
        Returns:
            Standardized schema dictionary
        """
        # Reuse Spider serializer logic since formats are similar
        from .spider_schema_serializer import SpiderSchemaSerializer
        
        spider_serializer = SpiderSchemaSerializer(self.data_dir.parent if self.data_dir.name == "bird" else self.data_dir)
        return spider_serializer.extract_schema_from_database_info(db_info)
    
    def extract_schema_from_table_data(self, table_data: Dict) -> Dict:
        """
        Extract schema from table data (for compatibility with WikiSQL interface).
        
        This method handles both single-table (WikiSQL) and multi-table (BIRD) formats.
        
        Args:
            table_data: Table or database schema dictionary
            
        Returns:
            Standardized schema dictionary
        """
        # Check if it's BIRD/Spider format (has db_id and table_names)
        if 'db_id' in table_data and 'table_names' in table_data:
            return self.extract_schema_from_database_info(table_data)
        
        # Otherwise, assume it's already in the right format or single-table
        return table_data
    
    def get_table_data_from_database(self, db_id: str, table_name: str, limit: int = 5) -> List[List]:
        """
        Get sample data from a database table.
        
        Args:
            db_id: Database identifier
            table_name: Table name
            limit: Number of rows to retrieve
            
        Returns:
            List of rows (each row is a list of values)
        """
        from ..loaders.bird_loader import BIRDLoader
        
        loader = BIRDLoader(self.data_dir.parent if self.data_dir.name == "bird" else self.data_dir)
        conn = loader.get_database_connection(db_id)
        
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            rows = cursor.fetchall()
            conn.close()
            return [list(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching data from {db_id}.{table_name}: {e}")
            if conn:
                conn.close()
            return []
