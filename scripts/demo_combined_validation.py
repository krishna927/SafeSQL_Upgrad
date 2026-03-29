"""Demo script showing Schema Validator and Constraint Checker working together.

This demonstrates the combined validation pipeline:
1. Schema Validator - checks tables/columns/types
2. Constraint Checker - checks operators/aggregations/logic
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification import SchemaValidator, ConstraintChecker
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo combined validation."""
    print("=" * 70)
    print("Combined Validation - Schema Validator + Constraint Checker")
    print("=" * 70)
    print("\nThis demonstrates the complete validation pipeline:\n")
    print("1. Schema Validator - Checks tables, columns, types")
    print("2. Constraint Checker - Checks operators, aggregations, logic\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing validators...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    schema_validator = SchemaValidator()
    constraint_checker = ConstraintChecker()
    print("   Status: All components initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries...")
    samples = loader.get_sample("dev", n=3)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("COMBINED VALIDATION RESULTS")
    print("=" * 70)
    
    for i, sample in enumerate(samples, 1):
        sql = sample['sql_string']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"SQL: {sql}\n")
        
        # Step 1: Schema Validation
        print("  [1] Schema Validation:")
        schema_result = schema_validator.validate(sql, schema)
        if schema_result['valid']:
            print("      Status: Schema validation passed")
        else:
            print("      Status: Schema validation failed")
            for error in schema_result['errors']:
                print(f"         - {error}")
        
        # Step 2: Constraint Checking
        print("  [2] Constraint Checking:")
        constraint_result = constraint_checker.check_constraints(sql, schema)
        if constraint_result['valid']:
            print("      Status: Constraint checking passed")
        else:
            print("      Status: Constraint violations detected")
            for violation in constraint_result['violations']:
                print(f"         - {violation}")
        
        # Overall result
        overall_valid = schema_result['valid'] and constraint_result['valid']
        print(f"\n  Result: {'SAFE TO EXECUTE' if overall_valid else 'UNSAFE'}")
        
        # Show warnings if any
        all_warnings = schema_result.get('warnings', []) + constraint_result.get('warnings', [])
        if all_warnings:
            print("  Warnings:")
            for warning in all_warnings:
                print(f"      - {warning}")
    
    # Test with invalid query
    print("\n" + "=" * 70)
    print("TESTING INVALID QUERY")
    print("=" * 70)
    
    if samples:
        sample_schema = serializer.extract_schema_from_table_data(samples[0]['table_schema'])
        table_name = sample_schema['table_name']
        
        # Invalid query: wrong column + wrong operator
        invalid_sql = f"SELECT InvalidColumn FROM {table_name} WHERE Position > 'Guard'"
        print(f"\nInvalid SQL: {invalid_sql}\n")
        
        print("  [1] Schema Validation:")
        schema_result = schema_validator.validate(invalid_sql, sample_schema)
        if not schema_result['valid']:
            print("      Status: Schema validation failed")
            for error in schema_result['errors']:
                print(f"         - {error}")
        
        print("  [2] Constraint Checking:")
        constraint_result = constraint_checker.check_constraints(invalid_sql, sample_schema)
        if not constraint_result['valid']:
            print("      Status: Constraint violations detected")
            for violation in constraint_result['violations']:
                print(f"         - {violation}")
        
        overall_valid = schema_result['valid'] and constraint_result['valid']
        print(f"\n  Result: {'SAFE TO EXECUTE' if overall_valid else 'UNSAFE - REJECTED'}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nBoth validators work together to ensure SQL safety:")
    print("- Schema Validator: Ensures SQL references valid database objects")
    print("- Constraint Checker: Ensures SQL operations are logically sound")
    print("\nTogether, they provide comprehensive SQL validation!")


if __name__ == "__main__":
    main()
