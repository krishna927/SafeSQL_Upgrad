"""Demo script to show Schema Validator in action.

This demonstrates:
1. How Schema Validator validates SQL against database schemas
2. Validation of tables, columns, and data types
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification.schema_validator import SchemaValidator
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Schema Validator."""
    print("=" * 70)
    print("Schema Validator - DEMO")
    print("=" * 70)
    print("\nThis demonstrates how Schema Validator works.")
    print("Testing with gold standard SQL from WikiSQL_VALUE dataset\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing validator...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    validator = SchemaValidator()
    print("   Status: All components initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries with schemas...")
    samples = loader.get_sample("dev", n=5)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("VALIDATION RESULTS")
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
        print(f"Table: {schema['table_name']}")
        print(f"Columns in schema: {[col['name'] for col in schema['columns']]}")
        
        # Validate
        result = validator.validate(sql, schema)
        
        if result['valid']:
            print(f"\nStatus: Validation passed")
            valid_count += 1
        else:
            print(f"\nStatus: Validation failed")
            invalid_count += 1
            for error in result['errors']:
                print(f"   Error: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"   Warning: {warning}")
        
        # Show details
        print(f"\n   Details:")
        print(f"   - Tables valid: {result['details']['tables_valid']}")
        print(f"   - Columns valid: {result['details']['columns_valid']}")
        print(f"   - Types valid: {result['details']['types_valid']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Valid queries: {valid_count}")
    print(f"Invalid queries: {invalid_count}")
    print(f"Total tested: {len(samples)}")
    
    print("\n" + "=" * 70)
    print("SCHEMA VALIDATOR COMPLETE")
    print("=" * 70)
    print("\nThe Schema Validator checks SQL against database schemas.")
    print("It validates tables, columns, and data types regardless of SQL source.")


if __name__ == "__main__":
    main()
