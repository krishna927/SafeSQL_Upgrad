"""Schema validation for SQL queries.

This module validates that SQL queries are compatible with database schemas.
It checks:
- Table existence
- Column existence
- Column type compatibility
- Operation compatibility with types
"""

from typing import Dict, List, Optional, Tuple, Set
import logging
import re

from ..utils.logger import get_logger
from ..utils.sql_parser import SQLParser

logger = get_logger(__name__)


class SchemaValidator:
    """Validates SQL queries against database schemas."""
    
    def __init__(self):
        """Initialize schema validator."""
        self.sql_parser = SQLParser()
        logger.info("SchemaValidator initialized")
    
    def validate(self, sql: str, schema: Dict) -> Dict:
        """
        Validate SQL query against schema.
        
        Args:
            sql: SQL query string
            schema: Schema dictionary from schema_serializer format
            
        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "details": {
                    "tables_valid": bool,
                    "columns_valid": bool,
                    "types_valid": bool,
                    ...
                }
            }
        """
        errors = []
        warnings = []
        details = {
            "tables_valid": True,
            "columns_valid": True,
            "types_valid": True,
            "operations_valid": True
        }
        
        # Extract table and column information from SQL
        tables_in_sql = self.sql_parser.get_tables(sql)
        columns_in_sql = self.sql_parser.get_columns(sql)
        operation_type = self.sql_parser.get_operation_type(sql)
        
        # Validate tables
        table_validation = self._validate_tables(tables_in_sql, schema)
        if not table_validation["valid"]:
            errors.extend(table_validation["errors"])
            details["tables_valid"] = False
        
        # Validate columns
        column_validation = self._validate_columns(columns_in_sql, schema, sql)
        if not column_validation["valid"]:
            errors.extend(column_validation["errors"])
            details["columns_valid"] = False
        warnings.extend(column_validation["warnings"])
        
        # Validate types and operations
        type_validation = self._validate_types(sql, schema)
        if not type_validation["valid"]:
            errors.extend(type_validation["errors"])
            details["types_valid"] = False
        warnings.extend(type_validation["warnings"])
        
        # Overall validation result
        is_valid = len(errors) == 0
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "details": details,
            "metadata": {
                "tables_found": list(tables_in_sql),
                "columns_found": list(columns_in_sql),
                "operation_type": operation_type
            }
        }
    
    def _validate_tables(self, tables_in_sql: Set[str], schema: Dict) -> Dict:
        """
        Validate that tables referenced in SQL exist in schema.
        
        Args:
            tables_in_sql: Set of table names found in SQL
            schema: Schema dictionary
            
        Returns:
            Validation result dictionary
        """
        errors = []
        schema_table_name = schema.get("table_name", "")
        
        # Normalize table names (remove quotes, handle case)
        normalized_schema_name = self._normalize_table_name(schema_table_name)
        normalized_sql_tables = {self._normalize_table_name(t) for t in tables_in_sql}
        
        # Check if any SQL table matches schema table
        if normalized_sql_tables:
            if normalized_schema_name not in normalized_sql_tables:
                # Check if it's a close match (for WikiSQL, table names might vary)
                found_match = False
                for sql_table in normalized_sql_tables:
                    # Check if table IDs match (WikiSQL format: table_10015132_11)
                    if self._extract_table_id(sql_table) == self._extract_table_id(normalized_schema_name):
                        found_match = True
                        break
                
                if not found_match:
                    errors.append(
                        f"Table '{list(tables_in_sql)[0]}' not found in schema. "
                        f"Schema table: '{schema_table_name}'"
                    )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_columns(self, columns_in_sql: Set[str], schema: Dict, sql: str) -> Dict:
        """
        Validate that columns referenced in SQL exist in schema.
        
        Args:
            columns_in_sql: Set of column names found in SQL
            schema: Schema dictionary
            sql: SQL query string (for context)
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        schema_columns = {col["name"] for col in schema.get("columns", [])}
        
        # Normalize column names (handle case, special characters)
        normalized_schema_cols = {self._normalize_column_name(c) for c in schema_columns}
        normalized_sql_cols = {self._normalize_column_name(c) for c in columns_in_sql}
        
        # Check each column in SQL
        for sql_col in columns_in_sql:
            normalized_sql_col = self._normalize_column_name(sql_col)
            
            # Direct match
            if normalized_sql_col in normalized_schema_cols:
                continue
            
            # Check for close matches (typos, case differences)
            close_matches = [
                sc for sc in schema_columns
                if self._normalize_column_name(sc) == normalized_sql_col
                or self._similar_column_name(sc, sql_col)
            ]
            
            if not close_matches:
                errors.append(
                    f"Column '{sql_col}' not found in schema. "
                    f"Available columns: {list(schema_columns)[:5]}..."
                )
            else:
                # Suggest correct column name
                warnings.append(
                    f"Column '{sql_col}' might be '{close_matches[0]}' "
                    f"(close match found)"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_types(self, sql: str, schema: Dict) -> Dict:
        """
        Validate that SQL operations are compatible with column types.
        
        Args:
            sql: SQL query string
            schema: Schema dictionary
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        # Check for aggregation functions
        aggregation_patterns = {
            "COUNT": r"COUNT\s*\(\s*(\w+)\s*\)",
            "SUM": r"SUM\s*\(\s*(\w+)\s*\)",
            "AVG": r"AVG\s*\(\s*(\w+)\s*\)",
            "MAX": r"MAX\s*\(\s*(\w+)\s*\)",
            "MIN": r"MIN\s*\(\s*(\w+)\s*\)"
        }
        
        schema_columns = {col["name"]: col for col in schema.get("columns", [])}
        
        sql_upper = sql.upper()
        
        for agg_func, pattern in aggregation_patterns.items():
            matches = re.findall(pattern, sql_upper, re.IGNORECASE)
            for col_name in matches:
                # Normalize column name
                normalized_col = self._normalize_column_name(col_name)
                
                # Find column in schema
                col_info = None
                for schema_col_name, schema_col_info in schema_columns.items():
                    if self._normalize_column_name(schema_col_name) == normalized_col:
                        col_info = schema_col_info
                        break
                
                if col_info:
                    col_type = col_info.get("type", "").upper()
                    
                    # Check type compatibility
                    if agg_func in ["SUM", "AVG"]:
                        if col_type not in ["INTEGER", "REAL", "NUMERIC"]:
                            errors.append(
                                f"Cannot use {agg_func} on column '{col_name}' "
                                f"(type: {col_type}). {agg_func} requires numeric type."
                            )
                    elif agg_func in ["MAX", "MIN"]:
                        # MAX/MIN work on most types, but warn for unusual cases
                        if col_type == "BLOB":
                            warnings.append(
                                f"Using {agg_func} on BLOB column '{col_name}' "
                                f"may not produce meaningful results"
                            )
                    # COUNT works on any type, no validation needed
        
        # Check WHERE clause value types
        where_validation = self._validate_where_clause_types(sql, schema_columns)
        errors.extend(where_validation["errors"])
        warnings.extend(where_validation["warnings"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_where_clause_types(self, sql: str, schema_columns: Dict[str, Dict]) -> Dict:
        """
        Validate WHERE clause condition types.
        
        Args:
            sql: SQL query string
            schema_columns: Dictionary mapping column names to column info
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        # Extract WHERE clause conditions
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|$)', sql, re.IGNORECASE)
        if not where_match:
            return {"valid": True, "errors": [], "warnings": []}
        
        where_clause = where_match.group(1)
        
        # Pattern: column operator value
        condition_pattern = r'(\w+)\s*([<>=!]+)\s*([^ANDOR]+)'
        conditions = re.findall(condition_pattern, where_clause, re.IGNORECASE)
        
        for col_name, operator, value in conditions:
            normalized_col = self._normalize_column_name(col_name.strip())
            
            # Find column in schema
            col_info = None
            for schema_col_name, schema_col_info in schema_columns.items():
                if self._normalize_column_name(schema_col_name) == normalized_col:
                    col_info = schema_col_info
                    break
            
            if col_info:
                col_type = col_info.get("type", "").upper()
                value_clean = value.strip().strip("'\"")
                
                # Check if value is numeric
                is_numeric_value = False
                try:
                    float(value_clean)
                    is_numeric_value = True
                except ValueError:
                    pass
                
                # Validate type compatibility
                if col_type in ["INTEGER", "REAL", "NUMERIC"]:
                    if not is_numeric_value and operator in [">", "<", ">=", "<="]:
                        warnings.append(
                            f"Comparison operator '{operator}' on numeric column "
                            f"'{col_name}' with non-numeric value '{value_clean}'"
                        )
                elif col_type == "TEXT":
                    if is_numeric_value and operator in [">", "<", ">=", "<="]:
                        warnings.append(
                            f"Comparison operator '{operator}' on text column "
                            f"'{col_name}' may not work as expected"
                        )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _normalize_table_name(self, table_name: str) -> str:
        """Normalize table name for comparison."""
        return table_name.lower().strip().replace('"', '').replace("'", "")
    
    def _normalize_column_name(self, column_name: str) -> str:
        """Normalize column name for comparison."""
        # Remove function calls, aliases, etc.
        col = column_name.split('(')[0].split('.')[-1].strip()
        return col.lower().replace('"', '').replace("'", "")
    
    def _extract_table_id(self, table_name: str) -> Optional[str]:
        """Extract table ID from WikiSQL table name (e.g., 'table_10015132_11' -> '10015132-11')."""
        # Pattern: table_10015132_11 -> 10015132-11
        match = re.search(r'table_(\d+)_(\d+)', table_name.lower())
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        return None
    
    def _similar_column_name(self, col1: str, col2: str) -> bool:
        """Check if two column names are similar (for typo detection)."""
        norm1 = self._normalize_column_name(col1)
        norm2 = self._normalize_column_name(col2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # Check edit distance (simple version)
        if abs(len(norm1) - len(norm2)) <= 2:
            # Simple similarity check
            common_chars = sum(1 for c in norm1 if c in norm2)
            similarity = common_chars / max(len(norm1), len(norm2))
            return similarity > 0.7
        
        return False


if __name__ == "__main__":
    # Test the validator
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
    from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 70)
    print("Schema Validator - Test")
    print("=" * 70)
    
    # Load sample data
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    
    samples = loader.get_sample("dev", n=5)
    
    validator = SchemaValidator()
    
    print(f"\nTesting validation on {len(samples)} sample queries...\n")
    
    for i, sample in enumerate(samples, 1):
        sql = sample['sql_string']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"--- Test {i} ---")
        print(f"SQL: {sql}")
        print(f"Table: {schema['table_name']}")
        
        result = validator.validate(sql, schema)
        
        if result['valid']:
            print(f"✅ VALID")
        else:
            print(f"❌ INVALID")
            for error in result['errors']:
                print(f"   Error: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"   ⚠️  Warning: {warning}")
        
        print()
