"""Test Spider fixes without API calls.

This script tests the table name fix by simulating SQL generation
and verifying that generic table names are replaced correctly.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.gpt4_generator import GPT4SQLGenerator
from src.data.loaders.dataset_factory import create_loader
from src.data.preprocessors.schema_serializer_factory import create_serializer


def test_table_name_fix():
    """Test that generic table names are fixed."""
    print("=" * 70)
    print("Testing Spider Table Name Fix")
    print("=" * 70)
    print("\nNOTE: This test does NOT make API calls - safe for testing!")
    print("=" * 70)
    
    # Load Spider sample
    loader = create_loader('spider')
    serializer = create_serializer('spider')
    samples = loader.get_sample('dev', n=3)
    
    generator = GPT4SQLGenerator()
    
    print("\n[TEST 1] Schema Formatting")
    print("-" * 70)
    for i, sample in enumerate(samples, 1):
        schema_data = sample.get('table_schema') or sample.get('database_schema', {})
        schema = serializer.extract_schema_from_table_data(schema_data)
        
        formatted = generator._format_schema(schema)
        
        print(f"\n--- Sample {i} ---")
        print(f"Question: {sample['query']['question'][:60]}...")
        
        # Check if table names are prominent
        if "CRITICAL" in formatted and "TABLE" in formatted.upper():
            print("[OK] Table names are prominently displayed")
        else:
            print("[FAIL] Table names not prominent enough")
        
        # Check if multiple tables are listed (for Spider)
        if "tables" in schema:
            table_names = schema.get("table_names", [])
            print(f"[INFO] Multi-table schema detected: {len(table_names)} tables")
            for tbl in table_names[:3]:
                if tbl in formatted:
                    print(f"  [OK] Table '{tbl}' found in formatted schema")
                else:
                    print(f"  [FAIL] Table '{tbl}' NOT found in formatted schema")
    
    print("\n[TEST 2] Generic Table Name Post-Processing")
    print("-" * 70)
    
    # Test cases
    test_cases = [
        {
            'sql': 'SELECT "Cylinders" FROM table GROUP BY "Cylinders"',
            'schema': {'table_names': ['CARS_DATA'], 'tables': {'CARS_DATA': {'columns': [{'name': 'Cylinders'}]}}},
            'expected': 'CARS_DATA'
        },
        {
            'sql': 'SELECT COUNT(*) FROM "table" WHERE "Year" = 2014',
            'schema': {'table_names': ['concert'], 'tables': {'concert': {'columns': [{'name': 'Year'}]}}},
            'expected': 'concert'
        },
        {
            'sql': 'SELECT * FROM table',
            'schema': {'table_names': ['museum', 'customer'], 'tables': {'museum': {'columns': []}, 'customer': {'columns': []}}},
            'expected': 'museum'  # First table as fallback
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input SQL: {test['sql']}")
        
        fixed_sql = generator._fix_generic_table_name(test['sql'], test['schema'])
        print(f"Fixed SQL: {fixed_sql}")
        
        if test['expected'] in fixed_sql:
            print(f"[OK] Generic 'table' replaced with '{test['expected']}'")
        else:
            print(f"[FAIL] Expected '{test['expected']}' but got: {fixed_sql}")
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print("\nIf all tests pass, the fixes are ready for evaluation.")
    print("Run: python scripts/run_models_spider_bird.py --spider_only --n_samples 10")


if __name__ == "__main__":
    test_table_name_fix()
