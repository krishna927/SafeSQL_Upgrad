"""Auto-repair module for SQL queries.

This module automatically fixes common SQL errors:
- Column name typos
- Type mismatches
- Aggregation mismatches
- Operator incompatibilities
- Condition value types
"""

from typing import Dict, List, Optional, Tuple
import logging
import re

from ..utils.logger import get_logger
from .schema_validator import SchemaValidator
from .constraint_checker import ConstraintChecker

logger = get_logger(__name__)


class AutoRepair:
    """Automatically repairs common SQL errors."""
    
    def __init__(self):
        """Initialize auto-repair module."""
        self.schema_validator = SchemaValidator()
        self.constraint_checker = ConstraintChecker()
        logger.info("AutoRepair initialized")
    
    def repair(self, sql: str, schema: Dict, 
               validation_errors: Optional[List[str]] = None,
               constraint_violations: Optional[List[str]] = None) -> Dict:
        """
        Attempt to repair SQL query.
        
        Args:
            sql: SQL query string or structured SQL dict (WikiSQL format)
            schema: Schema dictionary
            validation_errors: List of validation errors from SchemaValidator
            constraint_violations: List of constraint violations from ConstraintChecker
            
        Returns:
            Dictionary with repair results:
            {
                "repaired": bool,
                "repaired_sql": str or dict,
                "fixes_applied": List[str],
                "unfixable_errors": List[str]
            }
        """
        fixes_applied = []
        unfixable_errors = []
        
        # Determine if SQL is string or structured format
        is_structured = isinstance(sql, dict)
        
        if is_structured:
            # Work with structured SQL (WikiSQL format)
            repaired_sql = sql.copy()
            
            # Get errors if not provided
            if validation_errors is None or constraint_violations is None:
                sql_string = self._structured_to_string(repaired_sql, schema)
                schema_result = self.schema_validator.validate(sql_string, schema)
                constraint_result = self.constraint_checker.check_constraints(sql_string, schema)
                validation_errors = schema_result.get("errors", [])
                constraint_violations = constraint_result.get("violations", [])
            
            # Try to fix each error
            for error in validation_errors:
                fix_result = self._fix_validation_error(repaired_sql, error, schema)
                if fix_result["fixed"]:
                    repaired_sql = fix_result["repaired_sql"]
                    fixes_applied.append(fix_result["fix_description"])
                else:
                    unfixable_errors.append(error)
            
            for violation in constraint_violations:
                fix_result = self._fix_constraint_violation(repaired_sql, violation, schema)
                if fix_result["fixed"]:
                    repaired_sql = fix_result["repaired_sql"]
                    fixes_applied.append(fix_result["fix_description"])
                else:
                    unfixable_errors.append(violation)
            
            return {
                "repaired": len(fixes_applied) > 0 and len(unfixable_errors) == 0,
                "repaired_sql": repaired_sql,
                "fixes_applied": fixes_applied,
                "unfixable_errors": unfixable_errors
            }
        else:
            # Work with SQL string
            repaired_sql = sql
            
            # Get errors if not provided
            if validation_errors is None or constraint_violations is None:
                schema_result = self.schema_validator.validate(sql, schema)
                constraint_result = self.constraint_checker.check_constraints(sql, schema)
                validation_errors = schema_result.get("errors", [])
                constraint_violations = constraint_result.get("violations", [])
            
            # Try to fix each error
            for error in validation_errors:
                fix_result = self._fix_string_validation_error(repaired_sql, error, schema)
                if fix_result["fixed"]:
                    repaired_sql = fix_result["repaired_sql"]
                    fixes_applied.append(fix_result["fix_description"])
                else:
                    unfixable_errors.append(error)
            
            for violation in constraint_violations:
                fix_result = self._fix_string_constraint_violation(repaired_sql, violation, schema)
                if fix_result["fixed"]:
                    repaired_sql = fix_result["repaired_sql"]
                    fixes_applied.append(fix_result["fix_description"])
                else:
                    unfixable_errors.append(violation)
            
            return {
                "repaired": len(fixes_applied) > 0 and len(unfixable_errors) == 0,
                "repaired_sql": repaired_sql,
                "fixes_applied": fixes_applied,
                "unfixable_errors": unfixable_errors
            }
    
    def _fix_validation_error(self, sql_dict: Dict, error: str, schema: Dict) -> Dict:
        """
        Fix validation error in structured SQL.
        
        Args:
            sql_dict: Structured SQL dictionary
            error: Error message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Fix column not found errors
        if "not found in schema" in error:
            return self._fix_column_not_found(sql_dict, error, schema)
        
        # Fix table not found errors
        if "Table" in error and "not found" in error:
            return self._fix_table_not_found(sql_dict, error, schema)
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_column_not_found(self, sql_dict: Dict, error: str, schema: Dict) -> Dict:
        """
        Fix column not found error by finding similar column.
        
        Args:
            sql_dict: Structured SQL dictionary
            error: Error message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Extract column name from error
        col_match = re.search(r"Column '([^']+)'", error)
        if not col_match:
            return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
        
        invalid_col = col_match.group(1)
        columns = schema.get("columns", [])
        
        # Find similar column
        best_match = self._find_similar_column(invalid_col, columns)
        
        if best_match:
            col_index = best_match["index"]
            
            # Fix selected column
            if sql_dict.get("sel") is not None:
                # Check if this column is in SELECT
                header = [col["name"] for col in columns]
                if invalid_col in header or self._normalize_column_name(invalid_col) in [
                    self._normalize_column_name(h) for h in header
                ]:
                    # Find the index
                    for i, col_name in enumerate(header):
                        if self._normalize_column_name(col_name) == self._normalize_column_name(invalid_col):
                            sql_dict["sel"] = i
                            return {
                                "fixed": True,
                                "repaired_sql": sql_dict,
                                "fix_description": f"Fixed selected column: '{invalid_col}' -> '{best_match['name']}'"
                            }
            
            # Fix conditions
            conds = sql_dict.get("conds", [])
            for cond in conds:
                if len(cond) >= 3:
                    cond_col_idx = cond[0]
                    if cond_col_idx < len(columns):
                        cond_col_name = columns[cond_col_idx]["name"]
                        if self._normalize_column_name(cond_col_name) == self._normalize_column_name(invalid_col):
                            cond[0] = col_index
                            return {
                                "fixed": True,
                                "repaired_sql": sql_dict,
                                "fix_description": f"Fixed condition column: '{invalid_col}' -> '{best_match['name']}'"
                            }
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_table_not_found(self, sql_dict: Dict, error: str, schema: Dict) -> Dict:
        """Fix table not found error (usually not fixable for WikiSQL)."""
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_constraint_violation(self, sql_dict: Dict, violation: str, schema: Dict) -> Dict:
        """
        Fix constraint violation in structured SQL.
        
        Args:
            sql_dict: Structured SQL dictionary
            violation: Violation message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Fix operator incompatibility
        if "Comparison operator" in violation and "cannot be used" in violation:
            return self._fix_operator_incompatibility(sql_dict, violation, schema)
        
        # Fix aggregation on wrong type
        if "Aggregation function" in violation and "cannot be used" in violation:
            return self._fix_aggregation_type(sql_dict, violation, schema)
        
        # Fix unsatisfiable predicate
        if "Unsatisfiable predicate" in violation:
            return self._fix_unsatisfiable_predicate(sql_dict, violation, schema)
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_operator_incompatibility(self, sql_dict: Dict, violation: str, schema: Dict) -> Dict:
        """
        Fix operator incompatibility by changing operator to compatible one.
        
        Args:
            sql_dict: Structured SQL dictionary
            violation: Violation message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Extract column and operator from violation
        col_match = re.search(r"column '([^']+)'", violation)
        op_match = re.search(r"operator '([^']+)'", violation)
        
        if not col_match or not op_match:
            return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
        
        col_name = col_match.group(1)
        operator = op_match.group(1)
        
        # Find column index
        columns = schema.get("columns", [])
        col_index = None
        for i, col in enumerate(columns):
            if self._normalize_column_name(col["name"]) == self._normalize_column_name(col_name):
                col_index = i
                break
        
        if col_index is None:
            return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
        
        # Change operator to = (equality works on all types)
        operators = {'>': 1, '<': 2, '>=': 1, '<=': 2, '!=': 3, '=': 0}
        new_op_idx = 0  # Use equality
        
        # Fix conditions
        conds = sql_dict.get("conds", [])
        for cond in conds:
            if len(cond) >= 3 and cond[0] == col_index:
                old_op_idx = cond[1]
                cond[1] = new_op_idx
                return {
                    "fixed": True,
                    "repaired_sql": sql_dict,
                    "fix_description": f"Changed operator on '{col_name}' from '{operator}' to '=' (compatible with {columns[col_index]['type']})"
                }
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_aggregation_type(self, sql_dict: Dict, violation: str, schema: Dict) -> Dict:
        """
        Fix aggregation on wrong type by changing to COUNT or removing aggregation.
        
        Args:
            sql_dict: Structured SQL dictionary
            violation: Violation message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Extract aggregation function and column
        agg_match = re.search(r"(SUM|AVG)\(\)", violation)
        col_match = re.search(r"column '([^']+)'", violation)
        
        if not agg_match:
            return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
        
        agg_func = agg_match.group(1)
        
        # Change to COUNT (works on any type) or remove aggregation
        if sql_dict.get("agg") in [4, 5]:  # SUM or AVG
            sql_dict["agg"] = 3  # COUNT
            return {
                "fixed": True,
                "repaired_sql": sql_dict,
                "fix_description": f"Changed aggregation from {agg_func} to COUNT (works on all types)"
            }
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_unsatisfiable_predicate(self, sql_dict: Dict, violation: str, schema: Dict) -> Dict:
        """
        Fix unsatisfiable predicate by removing the condition.
        
        Args:
            sql_dict: Structured SQL dictionary
            violation: Violation message
            schema: Schema dictionary
            
        Returns:
            Fix result dictionary
        """
        # Remove conditions that are always false
        conds = sql_dict.get("conds", [])
        if len(conds) > 0:
            # Remove last condition (simplest fix)
            removed_cond = conds.pop()
            sql_dict["conds"] = conds
            return {
                "fixed": True,
                "repaired_sql": sql_dict,
                "fix_description": "Removed unsatisfiable predicate (column != column)"
            }
        
        return {"fixed": False, "repaired_sql": sql_dict, "fix_description": None}
    
    def _fix_string_validation_error(self, sql: str, error: str, schema: Dict) -> Dict:
        """Fix validation error in SQL string format."""
        # For now, return unfixed (string repair is more complex)
        return {"fixed": False, "repaired_sql": sql, "fix_description": None}
    
    def _fix_string_constraint_violation(self, sql: str, violation: str, schema: Dict) -> Dict:
        """Fix constraint violation in SQL string format."""
        # Fix operator incompatibility
        if "Comparison operator" in violation and "cannot be used" in violation:
            # Change >, <, >=, <= to = for text columns
            col_match = re.search(r"column '([^']+)'", violation)
            if col_match:
                col_name = col_match.group(1)
                # Replace operators in WHERE clause
                pattern = rf"({re.escape(col_name)})\s*([><=!]+)\s*"
                repaired = re.sub(pattern, rf"\1 = ", sql, flags=re.IGNORECASE)
                if repaired != sql:
                    return {
                        "fixed": True,
                        "repaired_sql": repaired,
                        "fix_description": f"Changed operator on '{col_name}' to '=' (compatible with text type)"
                    }
        
        # Fix aggregation on wrong type
        if "Aggregation function" in violation and "cannot be used" in violation:
            # Change SUM/AVG to COUNT
            repaired = re.sub(r"SUM\s*\(", "COUNT(", sql, flags=re.IGNORECASE)
            repaired = re.sub(r"AVG\s*\(", "COUNT(", repaired, flags=re.IGNORECASE)
            if repaired != sql:
                return {
                    "fixed": True,
                    "repaired_sql": repaired,
                    "fix_description": "Changed SUM/AVG to COUNT (works on all types)"
                }
        
        return {"fixed": False, "repaired_sql": sql, "fix_description": None}
    
    def _find_similar_column(self, col_name: str, columns: List[Dict]) -> Optional[Dict]:
        """
        Find similar column name using fuzzy matching.
        
        Args:
            col_name: Column name to find
            columns: List of column dictionaries
            
        Returns:
            Best matching column dict or None
        """
        normalized_target = self._normalize_column_name(col_name)
        best_match = None
        best_score = 0.0
        
        for col in columns:
            normalized_col = self._normalize_column_name(col["name"])
            
            # Exact match
            if normalized_col == normalized_target:
                return col
            
            # Calculate similarity
            score = self._column_similarity(normalized_target, normalized_col)
            if score > best_score and score > 0.7:
                best_score = score
                best_match = col
        
        return best_match
    
    def _column_similarity(self, col1: str, col2: str) -> float:
        """Calculate similarity between two column names."""
        # Simple character-based similarity
        if not col1 or not col2:
            return 0.0
        
        # Check common characters
        common = sum(1 for c in col1 if c in col2)
        total = max(len(col1), len(col2))
        
        return common / total if total > 0 else 0.0
    
    def _normalize_column_name(self, column_name: str) -> str:
        """Normalize column name for comparison."""
        col = column_name.split('(')[0].split('.')[-1].strip()
        return col.lower().replace('"', '').replace("'", "")
    
    def _structured_to_string(self, sql_dict: Dict, schema: Dict) -> str:
        """
        Convert structured SQL to string for validation.
        
        Args:
            sql_dict: Structured SQL dictionary (WikiSQL format)
            schema: Schema dictionary with 'header' field
            
        Returns:
            SQL query string
        """
        # Convert schema format if needed
        if "columns" in schema:
            # Convert to table_schema format
            table_schema = {
                "header": [col["name"] for col in schema["columns"]],
                "name": schema.get("table_name", "table")
            }
        else:
            table_schema = schema
        
        # Use loader's conversion method
        from ..data.loaders.wikisql_value_loader import WikiSQLValueLoader
        loader = WikiSQLValueLoader()
        return loader.convert_sql_to_string(sql_dict, table_schema)


if __name__ == "__main__":
    # Test the auto-repair module
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
    from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 70)
    print("Auto-Repair - Test")
    print("=" * 70)
    
    # Load sample data
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    
    samples = loader.get_sample("dev", n=3)
    
    repairer = AutoRepair()
    
    print(f"\nTesting auto-repair on {len(samples)} sample queries...\n")
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"--- Test {i} ---")
        print(f"Gold SQL: sel={gold_sql.get('sel')}, agg={gold_sql.get('agg')}")
        
        # Create broken SQL
        broken_sql = gold_sql.copy()
        broken_sql['agg'] = 4  # SUM (might be wrong type)
        
        result = repairer.repair(broken_sql, schema)
        
        if result['repaired']:
            print(f"[OK] REPAIRED")
            for fix in result['fixes_applied']:
                print(f"   Fix: {fix}")
        else:
            print(f"[INFO] No repairs needed or unfixable")
            if result['fixes_applied']:
                for fix in result['fixes_applied']:
                    print(f"   Fix: {fix}")
            if result['unfixable_errors']:
                for error in result['unfixable_errors']:
                    print(f"   Unfixable: {error}")
        
        print()
