"""Constraint checking for SQL queries.

This module validates SQL query constraints:
- Operator compatibility with column types
- Logical constraint violations
- Aggregation function correctness
- SQL structure constraints
"""

from typing import Dict, List, Optional, Set
import logging
import re

from ..utils.logger import get_logger
from ..utils.sql_parser import SQLParser

logger = get_logger(__name__)


class ConstraintChecker:
    """Checks SQL query constraints and logical correctness."""
    
    def __init__(self):
        """Initialize constraint checker."""
        self.sql_parser = SQLParser()
        logger.info("ConstraintChecker initialized")
    
    def check_constraints(self, sql: str, schema: Dict) -> Dict:
        """
        Check SQL query constraints.
        
        Args:
            sql: SQL query string
            schema: Schema dictionary from schema_serializer format
            
        Returns:
            Dictionary with constraint check results:
            {
                "valid": bool,
                "violations": List[str],
                "warnings": List[str],
                "details": {
                    "operator_compatibility": bool,
                    "aggregation_correctness": bool,
                    "logical_constraints": bool,
                    "structure_valid": bool
                }
            }
        """
        violations = []
        warnings = []
        details = {
            "operator_compatibility": True,
            "aggregation_correctness": True,
            "logical_constraints": True,
            "structure_valid": True
        }
        
        # Check operator compatibility
        operator_check = self._check_operator_compatibility(sql, schema)
        if not operator_check["valid"]:
            violations.extend(operator_check["violations"])
            details["operator_compatibility"] = False
        warnings.extend(operator_check["warnings"])
        
        # Check aggregation correctness
        aggregation_check = self._check_aggregation_correctness(sql, schema)
        if not aggregation_check["valid"]:
            violations.extend(aggregation_check["violations"])
            details["aggregation_correctness"] = False
        warnings.extend(aggregation_check["warnings"])
        
        # Check logical constraints
        logical_check = self._check_logical_constraints(sql, schema)
        if not logical_check["valid"]:
            violations.extend(logical_check["violations"])
            details["logical_constraints"] = False
        warnings.extend(logical_check["warnings"])
        
        # Check SQL structure
        structure_check = self._check_sql_structure(sql)
        if not structure_check["valid"]:
            violations.extend(structure_check["violations"])
            details["structure_valid"] = False
        warnings.extend(structure_check["warnings"])
        
        # Overall validation result
        is_valid = len(violations) == 0
        
        return {
            "valid": is_valid,
            "violations": violations,
            "warnings": warnings,
            "details": details
        }
    
    def _check_operator_compatibility(self, sql: str, schema: Dict) -> Dict:
        """
        Check if operators in WHERE clause are compatible with column types.
        
        Args:
            sql: SQL query string
            schema: Schema dictionary
            
        Returns:
            Validation result dictionary
        """
        violations = []
        warnings = []
        
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|$)', sql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return {"valid": True, "violations": [], "warnings": []}
        
        where_clause = where_match.group(1)
        
        # Get column info from schema
        schema_columns = {col["name"]: col for col in schema.get("columns", [])}
        
        # Split by AND/OR to get individual conditions
        conditions = re.split(r'\s+(?:AND|OR)\s+', where_clause, flags=re.IGNORECASE)
        
        for condition in conditions:
            condition = condition.strip()
            
            # Pattern: column operator value
            # Match: column_name operator value
            condition_pattern = r'([\w\s/]+?)\s*([<>=!]+)\s*(.+)'
            cond_match = re.match(condition_pattern, condition, re.IGNORECASE)
            
            if not cond_match:
                continue
            
            col_name = cond_match.group(1).strip()
            operator = cond_match.group(2).strip()
            value = cond_match.group(3).strip().strip("'\"")
            
            # Find column in schema
            col_info = None
            normalized_col = self._normalize_column_name(col_name)
            for schema_col_name, schema_col_info in schema_columns.items():
                if self._normalize_column_name(schema_col_name) == normalized_col:
                    col_info = schema_col_info
                    break
            
            if not col_info:
                continue  # Column validation handled by Schema Validator
            
            col_type = col_info.get("type", "").upper()
            
            # Check operator compatibility with type
            if operator in [">", "<", ">=", "<="]:
                # Comparison operators require numeric types
                if col_type not in ["INTEGER", "REAL", "NUMERIC"]:
                    violations.append(
                        f"Comparison operator '{operator}' cannot be used on column "
                        f"'{col_name}' (type: {col_type}). Use = or != for non-numeric types."
                    )
                else:
                    # Check if value is numeric
                    try:
                        float(value)
                    except ValueError:
                        warnings.append(
                            f"Comparison operator '{operator}' on numeric column "
                            f"'{col_name}' with non-numeric value '{value}'"
                        )
            
            elif operator == "=":
                # Equality works on all types, but check for type mismatches
                if col_type in ["INTEGER", "REAL", "NUMERIC"]:
                    # Check if value is numeric
                    try:
                        float(value)
                    except ValueError:
                        warnings.append(
                            f"Equality comparison on numeric column '{col_name}' "
                            f"with non-numeric value '{value}'"
                        )
            
            elif operator == "!=" or operator == "<>":
                # Inequality works on all types
                pass  # No specific constraints
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings
        }
    
    def _check_aggregation_correctness(self, sql: str, schema: Dict) -> Dict:
        """
        Check if aggregation functions are used correctly.
        
        Args:
            sql: SQL query string
            schema: Schema dictionary
            
        Returns:
            Validation result dictionary
        """
        violations = []
        warnings = []
        
        # Check for aggregation functions
        aggregation_patterns = {
            "COUNT": r"COUNT\s*\(\s*([^)]+)\s*\)",
            "SUM": r"SUM\s*\(\s*([^)]+)\s*\)",
            "AVG": r"AVG\s*\(\s*([^)]+)\s*\)",
            "MAX": r"MAX\s*\(\s*([^)]+)\s*\)",
            "MIN": r"MIN\s*\(\s*([^)]+)\s*\)"
        }
        
        schema_columns = {col["name"]: col for col in schema.get("columns", [])}
        sql_upper = sql.upper()
        
        for agg_func, pattern in aggregation_patterns.items():
            matches = re.findall(pattern, sql_upper, re.IGNORECASE)
            for col_expr in matches:
                # Extract column name (remove DISTINCT, etc.)
                col_expr_clean = col_expr.strip().upper()
                if col_expr_clean.startswith("DISTINCT "):
                    col_expr_clean = col_expr_clean.replace("DISTINCT ", "").strip()
                
                # Find column in schema
                col_info = None
                normalized_expr = self._normalize_column_name(col_expr)
                for schema_col_name, schema_col_info in schema_columns.items():
                    if self._normalize_column_name(schema_col_name) == normalized_expr:
                        col_info = schema_col_info
                        break
                
                if col_info:
                    col_type = col_info.get("type", "").upper()
                    
                    # Check aggregation compatibility
                    if agg_func in ["SUM", "AVG"]:
                        if col_type not in ["INTEGER", "REAL", "NUMERIC"]:
                            violations.append(
                                f"Aggregation function {agg_func}() cannot be used on column "
                                f"'{col_expr}' (type: {col_type}). {agg_func} requires numeric type."
                            )
                    
                    elif agg_func in ["MAX", "MIN"]:
                        # MAX/MIN work on most types, but warn for unusual cases
                        if col_type == "BLOB":
                            warnings.append(
                                f"Using {agg_func}() on BLOB column '{col_expr}' "
                                f"may not produce meaningful results"
                            )
                    
                    # COUNT works on any type, no validation needed
        
        # Check for aggregation without GROUP BY (if multiple columns selected)
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            has_aggregation = any(
                re.search(pattern, sql_upper, re.IGNORECASE)
                for pattern in aggregation_patterns.values()
            )
            
            if has_aggregation:
                # Check if there are non-aggregated columns
                # Remove aggregation functions
                select_no_agg = re.sub(
                    r'(?:COUNT|SUM|AVG|MAX|MIN)\s*\([^)]+\)',
                    '',
                    select_clause,
                    flags=re.IGNORECASE
                )
                # Check for remaining columns
                remaining_cols = [c.strip() for c in select_no_agg.split(',') if c.strip()]
                if len(remaining_cols) > 0 and any(col for col in remaining_cols if col.upper() not in ['DISTINCT', 'ALL']):
                    # Check for GROUP BY
                    has_group_by = re.search(r'GROUP\s+BY', sql, re.IGNORECASE)
                    if not has_group_by:
                        warnings.append(
                            "Aggregation function used with non-aggregated columns. "
                            "Consider using GROUP BY."
                        )
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings
        }
    
    def _check_logical_constraints(self, sql: str, schema: Dict) -> Dict:
        """
        Check logical constraints (unsatisfiable predicates, etc.).
        
        Args:
            sql: SQL query string
            schema: Schema dictionary
            
        Returns:
            Validation result dictionary
        """
        violations = []
        warnings = []
        
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|$)', sql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return {"valid": True, "violations": [], "warnings": []}
        
        where_clause = where_match.group(1)
        
        # Check for unsatisfiable predicates
        # Pattern: column != column (always false)
        unsatisfiable_pattern = r'(\w+)\s*!=\s*\1\b'
        if re.search(unsatisfiable_pattern, where_clause, re.IGNORECASE):
            violations.append(
                "Unsatisfiable predicate detected: column compared to itself with != operator. "
                "This condition will always be false."
            )
        
        # Pattern: column = column AND column != column (contradiction)
        # This is more complex and would require better parsing
        
        # Check for tautologies (always true conditions)
        # Pattern: column = column (always true)
        tautology_pattern = r'(\w+)\s*=\s*\1\b'
        if re.search(tautology_pattern, where_clause, re.IGNORECASE):
            warnings.append(
                "Tautology detected: column compared to itself with = operator. "
                "This condition is always true and may be unnecessary."
            )
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings
        }
    
    def _check_sql_structure(self, sql: str) -> Dict:
        """
        Check SQL structure constraints.
        
        Args:
            sql: SQL query string
            
        Returns:
            Validation result dictionary
        """
        violations = []
        warnings = []
        
        sql_upper = sql.upper().strip()
        
        # Check for basic SELECT structure
        if not sql_upper.startswith("SELECT"):
            violations.append("SQL query must start with SELECT")
        
        # Check for FROM clause
        if "FROM" not in sql_upper:
            violations.append("SQL query must contain a FROM clause")
        
        # Check for balanced parentheses
        open_parens = sql.count('(')
        close_parens = sql.count(')')
        if open_parens != close_parens:
            violations.append(
                f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing"
            )
        
        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("''")
        if single_quotes % 2 != 0:
            violations.append("Unbalanced single quotes in SQL string")
        
        # Check for ORDER BY without valid column
        order_by_match = re.search(r'ORDER\s+BY\s+([^,\s]+)', sql, re.IGNORECASE)
        if order_by_match:
            order_col = order_by_match.group(1).strip()
            # Basic check - column name should be alphanumeric or have special chars
            if not re.match(r'^[\w\s/]+$', order_col):
                warnings.append(
                    f"ORDER BY column '{order_col}' may be invalid"
                )
        
        # Check for GROUP BY without aggregation
        group_by_match = re.search(r'GROUP\s+BY', sql, re.IGNORECASE)
        if group_by_match:
            has_aggregation = re.search(
                r'(?:COUNT|SUM|AVG|MAX|MIN)\s*\(',
                sql_upper
            )
            if not has_aggregation:
                warnings.append(
                    "GROUP BY used without aggregation functions. "
                    "This may be unnecessary."
                )
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings
        }
    
    def _normalize_column_name(self, column_name: str) -> str:
        """Normalize column name for comparison."""
        col = column_name.split('(')[0].split('.')[-1].strip()
        return col.lower().replace('"', '').replace("'", "")


if __name__ == "__main__":
    # Test the constraint checker
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
    from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 70)
    print("Constraint Checker - Test")
    print("=" * 70)
    
    # Load sample data
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    
    samples = loader.get_sample("dev", n=5)
    
    checker = ConstraintChecker()
    
    print(f"\nTesting constraint checking on {len(samples)} sample queries...\n")
    
    for i, sample in enumerate(samples, 1):
        sql = sample['sql_string']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"--- Test {i} ---")
        print(f"SQL: {sql}")
        print(f"Table: {schema['table_name']}")
        
        result = checker.check_constraints(sql, schema)
        
        if result['valid']:
            print(f"[OK] CONSTRAINTS VALID")
        else:
            print(f"[ERROR] CONSTRAINT VIOLATIONS")
            for violation in result['violations']:
                print(f"   [ERROR] {violation}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"   [WARNING] {warning}")
        
        print()
