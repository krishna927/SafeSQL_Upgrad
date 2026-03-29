"""Verification Orchestrator for SafeSQL framework.

This module coordinates all verification components:
- Schema Validator
- Constraint Checker
- Semantic Analyzer
- Auto-Repair

It provides a unified interface for SQL verification and repair.
"""

from typing import Dict, List, Optional
import logging

from ..utils.logger import get_logger
from .schema_validator import SchemaValidator
from .constraint_checker import ConstraintChecker
from .semantic_analyzer import SemanticAnalyzer
from .auto_repair import AutoRepair

logger = get_logger(__name__)


class Verifier:
    """Main verification orchestrator that coordinates all validators."""
    
    def __init__(self, enable_repair: bool = True):
        """
        Initialize verifier.
        
        Args:
            enable_repair: Whether to enable auto-repair for fixable errors
        """
        self.schema_validator = SchemaValidator()
        self.constraint_checker = ConstraintChecker()
        self.semantic_analyzer = SemanticAnalyzer()
        self.auto_repair = AutoRepair() if enable_repair else None
        self.enable_repair = enable_repair
        
        logger.info(f"Verifier initialized (repair: {enable_repair})")
    
    def verify(self, sql: str, schema: Dict, question: Optional[str] = None,
               gold_sql: Optional[Dict] = None, max_repair_iterations: int = 1) -> Dict:
        """
        Verify SQL query and optionally repair errors.
        
        Args:
            sql: SQL query (string or structured dict)
            schema: Schema dictionary
            question: Optional natural language question
            gold_sql: Optional gold standard SQL for semantic comparison
            max_repair_iterations: Maximum number of repair attempts
            
        Returns:
            Dictionary with verification results:
            {
                "safe_to_execute": bool,
                "status": "SAFE" | "REPAIRABLE" | "UNSAFE",
                "repaired_sql": str or dict,
                "errors": List[str],
                "warnings": List[str],
                "validation_results": {
                    "schema": Dict,
                    "constraints": Dict,
                    "semantic": Optional[Dict]
                },
                "repair_applied": bool,
                "fixes_applied": List[str]
            }
        """
        is_structured = isinstance(sql, dict)
        current_sql = sql
        repair_applied = False
        fixes_applied = []
        all_errors = []
        all_warnings = []
        
        # Track validation results
        validation_results = {}
        
        # Iterate repair attempts
        for iteration in range(max_repair_iterations + 1):
            # Step 1: Schema Validation
            if is_structured:
                from ..data.loaders.wikisql_value_loader import WikiSQLValueLoader
                loader = WikiSQLValueLoader()
                sql_string = loader.convert_sql_to_string(
                    current_sql,
                    self._get_table_schema_for_loader(schema)
                )
            else:
                sql_string = current_sql
            
            schema_result = self.schema_validator.validate(sql_string, schema)
            validation_results["schema"] = schema_result
            
            # Step 2: Constraint Checking
            constraint_result = self.constraint_checker.check_constraints(sql_string, schema)
            validation_results["constraints"] = constraint_result
            
            # Step 3: Semantic Analysis (if gold SQL provided)
            semantic_result = None
            if gold_sql is not None and question is not None:
                if is_structured:
                    semantic_result = self.semantic_analyzer.analyze(
                        current_sql, gold_sql, question, schema
                    )
                else:
                    # For string SQL, semantic analysis would need conversion
                    pass
                validation_results["semantic"] = semantic_result
            
            # Collect errors and warnings
            current_errors = (
                schema_result.get("errors", []) +
                constraint_result.get("violations", [])
            )
            current_warnings = (
                schema_result.get("warnings", []) +
                constraint_result.get("warnings", [])
            )
            
            all_errors.extend(current_errors)
            all_warnings.extend(current_warnings)
            
            # Check if SQL is safe
            is_safe = (
                schema_result.get("valid", False) and
                constraint_result.get("valid", False)
            )
            
            if is_safe:
                # SQL is safe, no repair needed
                status = "SAFE"
                break
            
            # SQL has errors - attempt repair if enabled
            if self.enable_repair and self.auto_repair and iteration < max_repair_iterations:
                repair_result = self.auto_repair.repair(
                    current_sql,
                    schema,
                    validation_errors=schema_result.get("errors", []),
                    constraint_violations=constraint_result.get("violations", [])
                )
                
                if repair_result.get("repaired", False) and repair_result.get("fixes_applied"):
                    # Repair was successful
                    current_sql = repair_result["repaired_sql"]
                    fixes_applied.extend(repair_result.get("fixes_applied", []))
                    repair_applied = True
                    # Continue to next iteration to re-validate
                    continue
                else:
                    # Repair failed or no fixes applied
                    if repair_result.get("unfixable_errors"):
                        all_errors.extend(repair_result["unfixable_errors"])
                    status = "UNSAFE"
                    break
            else:
                # Repair disabled or max iterations reached
                if len(current_errors) == 0:
                    status = "SAFE"
                elif self.enable_repair:
                    status = "REPAIRABLE"
                else:
                    status = "UNSAFE"
                break
        else:
            # Exhausted repair iterations
            status = "UNSAFE"
        
        # Determine final status
        if is_safe:
            safe_to_execute = True
        elif status == "REPAIRABLE" and repair_applied:
            # Check if repaired SQL is now safe
            if is_structured:
                from ..data.loaders.wikisql_value_loader import WikiSQLValueLoader
                loader = WikiSQLValueLoader()
                repaired_string = loader.convert_sql_to_string(
                    current_sql,
                    self._get_table_schema_for_loader(schema)
                )
            else:
                repaired_string = current_sql
            
            final_schema_result = self.schema_validator.validate(repaired_string, schema)
            final_constraint_result = self.constraint_checker.check_constraints(repaired_string, schema)
            
            safe_to_execute = (
                final_schema_result.get("valid", False) and
                final_constraint_result.get("valid", False)
            )
            
            if safe_to_execute:
                status = "SAFE"
        else:
            safe_to_execute = False
        
        return {
            "safe_to_execute": safe_to_execute,
            "status": status,
            "repaired_sql": current_sql,
            "errors": list(set(all_errors)),  # Remove duplicates
            "warnings": list(set(all_warnings)),  # Remove duplicates
            "validation_results": validation_results,
            "repair_applied": repair_applied,
            "fixes_applied": fixes_applied
        }
    
    def _get_table_schema_for_loader(self, schema: Dict) -> Dict:
        """
        Convert schema format for loader compatibility.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            Table schema dictionary with 'header' and 'name' fields
        """
        if "columns" in schema:
            return {
                "header": [col["name"] for col in schema["columns"]],
                "name": schema.get("table_name", "table")
            }
        return schema


if __name__ == "__main__":
    # Test the verifier
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
    from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 70)
    print("Verifier - Test")
    print("=" * 70)
    
    # Load sample data
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    
    samples = loader.get_sample("dev", n=3)
    
    verifier = Verifier(enable_repair=True)
    
    print(f"\nTesting verifier on {len(samples)} sample queries...\n")
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"--- Test {i} ---")
        print(f"Question: {question}")
        print(f"SQL: sel={gold_sql.get('sel')}, agg={gold_sql.get('agg')}")
        
        result = verifier.verify(gold_sql, schema, question, gold_sql)
        
        print(f"\nStatus: {result['status']}")
        print(f"Safe to execute: {result['safe_to_execute']}")
        
        if result['repair_applied']:
            print(f"Repair applied: Yes")
            for fix in result['fixes_applied']:
                print(f"  Fix: {fix}")
        
        if result['errors']:
            print(f"Errors: {len(result['errors'])}")
            for error in result['errors'][:2]:
                print(f"  - {error}")
        
        print()
