"""Schema extraction and serialization for WikiSQL_VALUE dataset.

This module extracts table schemas from WikiSQL_VALUE format and serializes
them to a standardized JSON format suitable for SafeSQL framework.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class WikiSQLValueSchemaSerializer:
    """Extract and serialize schemas from WikiSQL_VALUE dataset."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize schema serializer.
        
        Args:
            data_dir: Path to WikiSQL_VALUE extracted data directory
        """
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data" / "datasets" / "wikisql_value" / "extracted" / "data"
        
        self.data_dir = Path(data_dir)
        logger.info(f"Initialized schema serializer with data_dir: {self.data_dir}")
    
    def extract_schema_from_table_data(self, table_data: Dict) -> Dict:
        """
        Extract schema information from WikiSQL_VALUE table data.
        
        WikiSQL_VALUE table format:
        {
            "id": "1-10015132-11",
            "name": "table_10015132_11",
            "header": ["Player", "No.", "Nationality", ...],
            "types": ["text", "text", "text", ...],
            "rows": [[...], [...]]
        }
        
        Args:
            table_data: Table dictionary from tables.jsonl
            
        Returns:
            Standardized schema dictionary
        """
        table_id = table_data.get('id', '')
        table_name = table_data.get('name', f'table_{table_id}')
        headers = table_data.get('header', [])
        types = table_data.get('types', [])
        rows = table_data.get('rows', [])
        
        # Infer SQL types from WikiSQL types
        sql_types = []
        for i, wiki_type in enumerate(types):
            sql_type = self._infer_sql_type(wiki_type, headers[i] if i < len(headers) else '', rows, i)
            sql_types.append(sql_type)
        
        # Build columns list
        # IMPORTANT: WikiSQL_VALUE database uses generic column names (col0, col1, etc.)
        # but schema provides human-readable names. We need both.
        columns = []
        for i, (header, sql_type) in enumerate(zip(headers, sql_types)):
            column_info = {
                "name": header,  # Human-readable name (for context)
                "db_name": f"col{i}",  # Database column name (for SQL generation)
                "type": sql_type,
                "index": i,
                "nullable": True,  # WikiSQL doesn't specify constraints
                "primary_key": False,
                "foreign_key": None
            }
            columns.append(column_info)
        
        # Build standardized schema
        schema = {
            "table_id": table_id,
            "table_name": table_name,
            "database_name": "wikisql_value",
            "columns": columns,
            "constraints": {
                "primary_keys": [],
                "foreign_keys": [],
                "unique_constraints": [],
                "check_constraints": []
            },
            "metadata": {
                "source": "WikiSQL_VALUE",
                "page_title": table_data.get('page_title', ''),
                "section_title": table_data.get('section_title', ''),
                "caption": table_data.get('caption', ''),
                "num_rows": len(rows),
                "sample_data": rows[:5] if rows else []  # Include sample rows
            }
        }
        
        return schema
    
    def _infer_sql_type(self, wiki_type: str, column_name: str, rows: List[List], col_index: int) -> str:
        """
        Infer SQL data type from WikiSQL type and sample data.
        
        Args:
            wiki_type: WikiSQL type (e.g., "text", "real")
            column_name: Column name (for heuristics)
            rows: Sample rows
            col_index: Column index
            
        Returns:
            SQL type string (e.g., "TEXT", "INTEGER", "REAL")
        """
        wiki_type_lower = wiki_type.lower()
        
        # WikiSQL type mapping
        if wiki_type_lower == "real":
            return "REAL"
        elif wiki_type_lower == "text":
            # Check if it's actually numeric
            numeric_count = 0
            for row in rows[:10]:  # Check first 10 rows
                if col_index < len(row):
                    value = row[col_index]
                    try:
                        float(value)
                        numeric_count += 1
                    except (ValueError, TypeError):
                        pass
            
            # If mostly numeric, might be INTEGER or REAL
            if numeric_count > len(rows[:10]) * 0.8:
                # Check if integers
                all_int = True
                for row in rows[:10]:
                    if col_index < len(row):
                        value = row[col_index]
                        try:
                            int(float(value))
                        except (ValueError, TypeError):
                            all_int = False
                            break
                if all_int:
                    return "INTEGER"
                return "REAL"
            
            return "TEXT"
        else:
            return "TEXT"  # Default to TEXT
    
    def extract_schema_from_database(self, table_id: str, split: str = "dev") -> Optional[Dict]:
        """
        Extract schema directly from SQLite database.
        
        Args:
            table_id: Table identifier
            split: Dataset split
            
        Returns:
            Schema dictionary or None if table not found
        """
        db_file = self.data_dir / f"{split}.db"
        if not db_file.exists():
            logger.warning(f"Database file not found: {db_file}")
            return None
        
        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Find table name from table_id
            # WikiSQL tables are named like "table_10015132_11"
            table_name = f"table_{table_id.replace('-', '_')}"
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            
            if not columns_info:
                logger.warning(f"Table {table_name} not found in database")
                conn.close()
                return None
            
            # Build columns list
            columns = []
            for col_info in columns_info:
                col_id, col_name, col_type, not_null, default_val, is_pk = col_info
                columns.append({
                    "name": col_name,
                    "type": col_type.upper() if col_type else "TEXT",
                    "index": col_id,
                    "nullable": not not_null,
                    "primary_key": bool(is_pk),
                    "foreign_key": None,
                    "default": default_val
                })
            
            # Get constraints
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = cursor.fetchall()
            
            schema = {
                "table_id": table_id,
                "table_name": table_name,
                "database_name": "wikisql_value",
                "columns": columns,
                "constraints": {
                    "primary_keys": [col["name"] for col in columns if col["primary_key"]],
                    "foreign_keys": [],
                    "unique_constraints": [],
                    "check_constraints": []
                },
                "metadata": {
                    "source": "WikiSQL_VALUE",
                    "extracted_from": "sqlite_database",
                    "split": split
                }
            }
            
            conn.close()
            return schema
            
        except Exception as e:
            logger.error(f"Error extracting schema from database: {e}")
            return None
    
    def serialize_schemas(self, split: str = "dev", output_file: Optional[Path] = None) -> Dict[str, Dict]:
        """
        Serialize all schemas from a split to JSON format.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            output_file: Optional path to save JSON file
            
        Returns:
            Dictionary mapping table_id to schema
        """
        from ..loaders.wikisql_value_loader import WikiSQLValueLoader
        
        loader = WikiSQLValueLoader(self.data_dir)
        tables = loader.load_tables(split)
        
        schemas = {}
        for table_id, table_data in tables.items():
            try:
                schema = self.extract_schema_from_table_data(table_data)
                schemas[table_id] = schema
            except Exception as e:
                logger.warning(f"Error serializing schema for {table_id}: {e}")
                continue
        
        # Save to file if specified
        if output_file:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schemas, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(schemas)} schemas to {output_file}")
        
        logger.info(f"Serialized {len(schemas)} schemas from {split} split")
        return schemas
    
    def serialize_all_splits(self, output_dir: Optional[Path] = None) -> Dict[str, Dict[str, Dict]]:
        """
        Serialize schemas for all splits (train, dev, test).
        
        Args:
            output_dir: Directory to save schema JSON files
            
        Returns:
            Dictionary mapping split to table_id to schema
        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / "data" / "schemas" / "wikisql_value"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_schemas = {}
        for split in ['train', 'dev', 'test']:
            output_file = output_dir / f"{split}_schemas.json"
            schemas = self.serialize_schemas(split, output_file)
            all_schemas[split] = schemas
        
        logger.info(f"Serialized schemas for all splits to {output_dir}")
        return all_schemas
    
    def load_serialized_schema(self, table_id: str, split: str = "dev", 
                              schema_dir: Optional[Path] = None) -> Optional[Dict]:
        """
        Load a serialized schema from JSON file.
        
        Args:
            table_id: Table identifier
            split: Dataset split
            schema_dir: Directory containing schema JSON files
            
        Returns:
            Schema dictionary or None if not found
        """
        if schema_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            schema_dir = project_root / "data" / "schemas" / "wikisql_value"
        
        schema_file = Path(schema_dir) / f"{split}_schemas.json"
        if not schema_file.exists():
            logger.warning(f"Schema file not found: {schema_file}")
            return None
        
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schemas = json.load(f)
            return schemas.get(table_id)
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            return None


if __name__ == "__main__":
    # Test the serializer
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("Testing WikiSQL_VALUE Schema Serializer")
    print("=" * 60)
    
    serializer = WikiSQLValueSchemaSerializer()
    
    # Serialize dev split schemas
    print("\nSerializing dev split schemas...")
    schemas = serializer.serialize_schemas("dev")
    
    print(f"\nSerialized {len(schemas)} schemas")
    
    if schemas:
        first_table_id = list(schemas.keys())[0]
        first_schema = schemas[first_table_id]
        
        print(f"\n--- Sample Schema: {first_table_id} ---")
        print(f"Table Name: {first_schema['table_name']}")
        print(f"Columns ({len(first_schema['columns'])}):")
        for col in first_schema['columns']:
            print(f"  - {col['name']} ({col['type']})")
        print(f"\nFull schema (first 500 chars):")
        schema_json = json.dumps(first_schema, indent=2)
        print(schema_json[:500] + "..." if len(schema_json) > 500 else schema_json)
