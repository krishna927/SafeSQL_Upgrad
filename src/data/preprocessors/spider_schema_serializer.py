"""Schema extraction and serialization for Spider dataset.

Spider dataset has multi-table databases with complex schemas including
foreign keys, primary keys, and relationships between tables.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SpiderSchemaSerializer:
    """Extract and serialize schemas from Spider dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize Spider schema serializer.
        
        Args:
            data_dir: Path to Spider dataset directory
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "spider"
        
        self.data_dir = Path(data_dir)
        self.database_dir = self.data_dir / "database"
        logger.info(f"Initialized Spider schema serializer with data_dir: {self.data_dir}")
    
    def extract_schema_from_database_info(self, db_info: Dict) -> Dict:
        """
        Extract schema from Spider database info dictionary.
        
        Spider format:
        {
            "db_id": "academic",
            "table_names_original": ["table1", "table2"],
            "table_names": ["table1", "table2"],
            "column_names_original": [[-1, "*"], [0, "col1"], [0, "col2"], [1, "col3"]],
            "column_names": [[-1, "*"], [0, "col1"], [0, "col2"], [1, "col3"]],
            "column_types": ["text", "text", "text", "text"],
            "foreign_keys": [[1, 2]],  # [column_index, referenced_column_index]
            "primary_keys": [0, 3]  # Column indices
        }
        
        Args:
            db_info: Database info dictionary from tables.json
            
        Returns:
            Standardized schema dictionary
        """
        db_id = db_info.get('db_id', '')
        table_names = db_info.get('table_names', [])
        table_names_original = db_info.get('table_names_original', table_names)
        column_names = db_info.get('column_names', [])
        column_names_original = db_info.get('column_names_original', column_names)
        column_types = db_info.get('column_types', [])
        foreign_keys = db_info.get('foreign_keys', [])
        primary_keys = db_info.get('primary_keys', [])
        
        # Build tables dictionary
        tables = {}
        current_table_idx = -1
        
        for col_idx, (table_idx, col_name) in enumerate(column_names):
            if table_idx == -1:  # Special marker for "*"
                continue
            
            if table_idx != current_table_idx:
                # New table
                current_table_idx = table_idx
                if table_idx < len(table_names):
                    table_name = table_names[table_idx]
                    table_name_original = table_names_original[table_idx] if table_idx < len(table_names_original) else table_name
                    
                    tables[table_name] = {
                        "name": table_name,
                        "name_original": table_name_original,
                        "columns": [],
                        "primary_keys": [],
                        "foreign_keys": []
                    }
            
            # Add column
            if table_idx < len(table_names):
                table_name = table_names[table_idx]
                col_type = column_types[col_idx] if col_idx < len(column_types) else "text"
                
                column_info = {
                    "name": col_name,
                    "type": self._normalize_type(col_type),
                    "index": col_idx,
                    "table_index": table_idx,
                    "nullable": col_idx not in primary_keys,
                    "primary_key": col_idx in primary_keys,
                    "foreign_key": None
                }
                
                tables[table_name]["columns"].append(column_info)
                
                if col_idx in primary_keys:
                    tables[table_name]["primary_keys"].append(col_name)
        
        # Process foreign keys
        for fk_pair in foreign_keys:
            if len(fk_pair) >= 2:
                col_idx, ref_col_idx = fk_pair[0], fk_pair[1]
                
                # Find which table this column belongs to
                if col_idx < len(column_names) and ref_col_idx < len(column_names):
                    col_table_idx, col_name = column_names[col_idx]
                    ref_table_idx, ref_col_name = column_names[ref_col_idx]
                    
                    if col_table_idx >= 0 and col_table_idx < len(table_names):
                        table_name = table_names[col_table_idx]
                        if table_name in tables:
                            # Find the column and update foreign key info
                            for col in tables[table_name]["columns"]:
                                if col["index"] == col_idx:
                                    col["foreign_key"] = {
                                        "referenced_table": table_names[ref_table_idx] if ref_table_idx >= 0 and ref_table_idx < len(table_names) else None,
                                        "referenced_column": ref_col_name
                                    }
                                    tables[table_name]["foreign_keys"].append({
                                        "column": col_name,
                                        "referenced_table": table_names[ref_table_idx] if ref_table_idx >= 0 and ref_table_idx < len(table_names) else None,
                                        "referenced_column": ref_col_name
                                    })
        
        # Build standardized schema (multi-table)
        schema = {
            "db_id": db_id,
            "database_name": db_id,
            "tables": tables,
            "table_names": table_names,
            "constraints": {
                "primary_keys": {table: tables[table]["primary_keys"] for table in tables},
                "foreign_keys": {table: tables[table]["foreign_keys"] for table in tables},
                "unique_constraints": [],
                "check_constraints": []
            },
            "metadata": {
                "source": "Spider",
                "num_tables": len(tables),
                "total_columns": sum(len(tables[t]["columns"]) for t in tables)
            }
        }
        
        return schema
    
    def extract_schema_for_table(self, db_info: Dict, table_name: str) -> Optional[Dict]:
        """
        Extract schema for a specific table within a database.
        
        Args:
            db_info: Database info dictionary
            table_name: Name of the table
            
        Returns:
            Single-table schema dictionary (WikiSQL-compatible format) or None
        """
        full_schema = self.extract_schema_from_database_info(db_info)
        
        if table_name not in full_schema["tables"]:
            return None
        
        table_info = full_schema["tables"][table_name]
        
        # Convert to single-table format (for compatibility)
        schema = {
            "table_id": f"{full_schema['db_id']}.{table_name}",
            "table_name": table_name,
            "database_name": full_schema["db_id"],
            "columns": table_info["columns"],
            "constraints": {
                "primary_keys": table_info["primary_keys"],
                "foreign_keys": table_info["foreign_keys"],
                "unique_constraints": [],
                "check_constraints": []
            },
            "metadata": {
                "source": "Spider",
                "db_id": full_schema["db_id"],
                "is_multi_table": True
            }
        }
        
        return schema
    
    def extract_schema_from_table_data(self, table_data: Dict) -> Dict:
        """
        Extract schema from table data (for compatibility with WikiSQL interface).
        
        This method handles both single-table (WikiSQL) and multi-table (Spider) formats.
        
        Args:
            table_data: Table or database schema dictionary
            
        Returns:
            Standardized schema dictionary
        """
        # Check if it's Spider format (has db_id and table_names)
        if 'db_id' in table_data and 'table_names' in table_data:
            return self.extract_schema_from_database_info(table_data)
        
        # Otherwise, assume it's already in the right format or single-table
        return table_data
    
    def _normalize_type(self, col_type: str) -> str:
        """
        Normalize column type to standard SQL types.
        
        Args:
            col_type: Column type string
            
        Returns:
            Normalized SQL type (TEXT, INTEGER, REAL, etc.)
        """
        col_type_upper = col_type.upper().strip()
        
        # SQLite type mapping
        type_mapping = {
            'TEXT': 'TEXT',
            'VARCHAR': 'TEXT',
            'CHAR': 'TEXT',
            'STRING': 'TEXT',
            'INTEGER': 'INTEGER',
            'INT': 'INTEGER',
            'BIGINT': 'INTEGER',
            'REAL': 'REAL',
            'FLOAT': 'REAL',
            'DOUBLE': 'REAL',
            'NUMERIC': 'REAL',
            'BOOLEAN': 'INTEGER',
            'BOOL': 'INTEGER',
            'DATE': 'TEXT',
            'DATETIME': 'TEXT',
            'TIMESTAMP': 'TEXT',
            'BLOB': 'BLOB'
        }
        
        return type_mapping.get(col_type_upper, 'TEXT')
    
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
        from ..loaders.spider_loader import SpiderLoader
        
        loader = SpiderLoader(self.data_dir.parent if self.data_dir.name == "spider" else self.data_dir)
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


if __name__ == "__main__":
    # Test the serializer
    import sys
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("Testing Spider Schema Serializer")
    print("=" * 60)
    
    try:
        serializer = SpiderSchemaSerializer()
        
        # Load tables.json
        tables_file = serializer.data_dir / "tables.json"
        if tables_file.exists():
            with open(tables_file, 'r', encoding='utf-8') as f:
                tables_data = json.load(f)
            
            if tables_data:
                first_db = tables_data[0]
                print(f"\nFirst database: {first_db.get('db_id', 'N/A')}")
                
                schema = serializer.extract_schema_from_database_info(first_db)
                print(f"\nSchema extracted:")
                print(f"  Database: {schema['database_name']}")
                print(f"  Tables: {len(schema['tables'])}")
                print(f"  Table names: {list(schema['tables'].keys())[:5]}")
                
                if schema['tables']:
                    first_table = list(schema['tables'].keys())[0]
                    table_schema = schema['tables'][first_table]
                    print(f"\n  First table '{first_table}':")
                    print(f"    Columns: {len(table_schema['columns'])}")
                    for col in table_schema['columns'][:5]:
                        print(f"      - {col['name']} ({col['type']})")
        else:
            print(f"\n[WARN] tables.json not found at {tables_file}")
            print("Please ensure Spider dataset is downloaded.")
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
