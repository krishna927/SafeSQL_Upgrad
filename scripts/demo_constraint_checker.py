"""Demo script to show Constraint Checker in action.

This demonstrates:
1. How Constraint Checker validates SQL structure and constraints
2. Detection of operator incompatibilities
3. Detection of logical constraint violations
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification.constraint_checker import ConstraintChecker
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Constraint Checker."""
    print("=" * 70)
    print("Constraint Checker - DEMO")
    print("=" * 70)
    print("\nThis demonstrates how Constraint Checker validates:")
    print("- Operator compatibility with column types")
    print("- Aggregation function correctness")
    print("- Logical constraint violations")
    print("- SQL structure constraints\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing checker...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    checker = ConstraintChecker()
    print("   Status: All components initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries with schemas...")
    samples = loader.get_sample("dev", n=5)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("CONSTRAINT CHECK RESULTS")
    print("=" * 70)
    
    valid_count = 0
    invalid_count = 0
    
    for i, sample in enumerate(samples, 1):
        sql = sample['sql_string']
        question = sample['query']['question']
        
        # Extract schema
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"SQL: {sql}")
        
        # Check constraints
        result = checker.check_constraints(sql, schema)
        
        if result['valid']:
            print(f"\nStatus: Constraints valid")
            valid_count += 1
        else:
            print(f"\nStatus: Constraint violations detected")
            invalid_count += 1
            for violation in result['violations']:
                print(f"   Violation: {violation}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"   Warning: {warning}")
        
        # Show details
        print(f"\n   Details:")
        print(f"   - Operator compatibility: {result['details']['operator_compatibility']}")
        print(f"   - Aggregation correctness: {result['details']['aggregation_correctness']}")
        print(f"   - Logical constraints: {result['details']['logical_constraints']}")
        print(f"   - Structure valid: {result['details']['structure_valid']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Valid queries: {valid_count}")
    print(f"Invalid queries: {invalid_count}")
    print(f"Total tested: {len(samples)}")
    
    # Test with intentionally invalid queries
    print("\n" + "=" * 70)
    print("TESTING WITH INVALID QUERIES")
    print("=" * 70)
    
    if samples:
        sample_schema = serializer.extract_schema_from_table_data(samples[0]['table_schema'])
        table_name = sample_schema['table_name']
        
        # Test 1: Invalid operator on text column
        invalid_sql1 = f"SELECT * FROM {table_name} WHERE Position > 'Guard'"
        print(f"\n--- Invalid Query 1: Comparison operator on text ---")
        print(f"SQL: {invalid_sql1}")
        result1 = checker.check_constraints(invalid_sql1, sample_schema)
        if not result1['valid']:
            print("Status: Violation detected")
            for violation in result1['violations']:
                print(f"   Violation: {violation}")
        
        # Test 2: SUM on text column
        invalid_sql2 = f"SELECT SUM(Position) FROM {table_name}"
        print(f"\n--- Invalid Query 2: SUM on text column ---")
        print(f"SQL: {invalid_sql2}")
        result2 = checker.check_constraints(invalid_sql2, sample_schema)
        if not result2['valid']:
            print("Status: Violation detected")
            for violation in result2['violations']:
                print(f"   Violation: {violation}")
        
        # Test 3: Unsatisfiable predicate
        invalid_sql3 = f"SELECT * FROM {table_name} WHERE Position != Position"
        print(f"\n--- Invalid Query 3: Unsatisfiable predicate ---")
        print(f"SQL: {invalid_sql3}")
        result3 = checker.check_constraints(invalid_sql3, sample_schema)
        if not result3['valid']:
            print("Status: Violation detected")
            for violation in result3['violations']:
                print(f"   Violation: {violation}")
    
    print("\n" + "=" * 70)
    print("CONSTRAINT CHECKER COMPLETE")
    print("=" * 70)
    print("\nThe Constraint Checker validates SQL structure and constraints.")
    print("It works alongside Schema Validator to ensure SQL safety.")


if __name__ == "__main__":
    main()
