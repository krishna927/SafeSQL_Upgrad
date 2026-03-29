"""Demo script to show Auto-Repair in action.

This demonstrates:
1. How Auto-Repair fixes common SQL errors
2. Automatic correction of operator incompatibilities
3. Aggregation type fixes
4. Column name corrections
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification import SchemaValidator, ConstraintChecker
from src.verification.auto_repair import AutoRepair
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Auto-Repair."""
    print("=" * 70)
    print("Auto-Repair - DEMO")
    print("=" * 70)
    print("\nThis demonstrates how Auto-Repair fixes common SQL errors:\n")
    print("- Operator incompatibilities (e.g., > on text columns)")
    print("- Aggregation type mismatches (e.g., SUM on text)")
    print("- Column name errors")
    print("- Unsatisfiable predicates\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing components...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    validator = SchemaValidator()
    constraint_checker = ConstraintChecker()
    repairer = AutoRepair()
    print("   Status: All components initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries...")
    samples = loader.get_sample("dev", n=3)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("AUTO-REPAIR RESULTS")
    print("=" * 70)
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"Gold SQL: sel={gold_sql.get('sel')}, agg={gold_sql.get('agg')}, "
              f"conds={len(gold_sql.get('conds', []))}")
        
        # Create broken SQL with common errors
        broken_sql = gold_sql.copy()
        
        # Error 1: Wrong aggregation type (SUM on text column)
        if broken_sql.get('agg', 0) == 0:
            broken_sql['agg'] = 4  # SUM
            print(f"\nCreated broken SQL: Changed aggregation to SUM")
        
        # Convert to string for validation
        sql_string = loader.convert_sql_to_string(broken_sql, sample['table_schema'])
        print(f"Broken SQL string: {sql_string}")
        
        # Validate broken SQL
        schema_result = validator.validate(sql_string, schema)
        constraint_result = constraint_checker.check_constraints(sql_string, schema)
        
        print(f"\nValidation errors found:")
        all_errors = schema_result.get('errors', []) + constraint_result.get('violations', [])
        for error in all_errors[:2]:  # Show first 2 errors
            print(f"  - {error}")
        
        # Attempt repair
        print(f"\nAttempting auto-repair...")
        repair_result = repairer.repair(
            broken_sql,
            schema,
            validation_errors=schema_result.get('errors', []),
            constraint_violations=constraint_result.get('violations', [])
        )
        
        if repair_result['repaired']:
            print(f"Status: SQL repaired successfully")
            for fix in repair_result['fixes_applied']:
                print(f"  Fix applied: {fix}")
            
            # Validate repaired SQL
            repaired_string = loader.convert_sql_to_string(
                repair_result['repaired_sql'],
                sample['table_schema']
            )
            print(f"\nRepaired SQL: {repaired_string}")
            
            repaired_schema_result = validator.validate(repaired_string, schema)
            repaired_constraint_result = constraint_checker.check_constraints(repaired_string, schema)
            
            if repaired_schema_result['valid'] and repaired_constraint_result['valid']:
                print(f"Status: Repaired SQL is now valid")
            else:
                print(f"Status: Repaired SQL still has issues")
        else:
            print(f"Repair status:")
            if repair_result['fixes_applied']:
                for fix in repair_result['fixes_applied']:
                    print(f"  Fix applied: {fix}")
            if repair_result['unfixable_errors']:
                print(f"  Unfixable errors:")
                for error in repair_result['unfixable_errors']:
                    print(f"    - {error}")
    
    # Test with string SQL format
    print("\n" + "=" * 70)
    print("TESTING STRING SQL REPAIR")
    print("=" * 70)
    
    if samples:
        sample = samples[0]
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        table_name = schema['table_name']
        
        # Create broken SQL string
        broken_sql_string = f"SELECT SUM(Position) FROM {table_name} WHERE Position > 'Guard'"
        print(f"\nBroken SQL: {broken_sql_string}")
        
        # Validate
        schema_result = validator.validate(broken_sql_string, schema)
        constraint_result = constraint_checker.check_constraints(broken_sql_string, schema)
        
        print(f"\nErrors found:")
        for error in schema_result.get('errors', []):
            print(f"  - {error}")
        for violation in constraint_result.get('violations', []):
            print(f"  - {violation}")
        
        # Repair
        repair_result = repairer.repair(
            broken_sql_string,
            schema,
            validation_errors=schema_result.get('errors', []),
            constraint_violations=constraint_result.get('violations', [])
        )
        
        if repair_result['repaired']:
            print(f"\nStatus: SQL repaired")
            print(f"  Repaired SQL: {repair_result['repaired_sql']}")
            for fix in repair_result['fixes_applied']:
                print(f"  Fix: {fix}")
        else:
            print(f"\nStatus: Could not fully repair")
            if repair_result['fixes_applied']:
                for fix in repair_result['fixes_applied']:
                    print(f"  Partial fix: {fix}")
    
    print("\n" + "=" * 70)
    print("AUTO-REPAIR COMPLETE")
    print("=" * 70)
    print("\nAuto-Repair automatically fixes common SQL errors detected by validators.")


if __name__ == "__main__":
    main()
