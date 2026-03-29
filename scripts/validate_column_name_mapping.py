"""Validate column name mapping for WikiSQL_VALUE and Spider datasets.

This script validates that schema-to-database column name mapping is correct
without making any API calls. It checks:
1. Schema structure (has db_name fields for WikiSQL_VALUE)
2. Table name mapping (table_XXX -> table_1_XXX for WikiSQL_VALUE)
3. Column name mapping (human-readable -> colX for WikiSQL_VALUE)
4. Database connectivity and actual column names
5. Prompt formatting (includes correct column names)

NO API CALLS - Safe for testing without costs.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.dataset_factory import create_loader
from src.data.preprocessors.schema_serializer_factory import create_serializer
from src.models.gpt4_generator import GPT4SQLGenerator


def validate_wikisql_schema(sample: Dict) -> Dict:
    """Validate WikiSQL_VALUE schema structure."""
    schema = sample.get('table_schema', {})
    issues = []
    checks_passed = []
    
    # Check 1: database_name field
    if schema.get('database_name') == 'wikisql_value':
        checks_passed.append("database_name field present")
    else:
        issues.append(f"Missing or incorrect database_name field: {schema.get('database_name')}")
    
    # Check 2: columns list exists
    if 'columns' in schema:
        checks_passed.append("columns list present")
        
        # Check 3: Each column has db_name
        columns = schema.get('columns', [])
        all_have_db_name = all('db_name' in col for col in columns)
        if all_have_db_name:
            checks_passed.append("All columns have db_name field")
        else:
            issues.append(f"Some columns missing db_name: {[col.get('name') for col in columns if 'db_name' not in col]}")
        
        # Check 4: db_name format is colX
        db_names = [col.get('db_name') for col in columns if 'db_name' in col]
        valid_format = all(name.startswith('col') and name[3:].isdigit() for name in db_names)
        if valid_format:
            checks_passed.append("All db_name fields use colX format")
        else:
            issues.append(f"Invalid db_name format: {[name for name in db_names if not (name.startswith('col') and name[3:].isdigit())]}")
    else:
        issues.append("Missing columns list in schema")
    
    # Check 5: Table name has table_1_ prefix
    table_name = schema.get('name', '')
    if table_name.startswith('table_1_'):
        checks_passed.append("Table name has correct table_1_ prefix")
    elif table_name.startswith('table_'):
        issues.append(f"Table name missing '1_' prefix: {table_name}")
    else:
        issues.append(f"Unexpected table name format: {table_name}")
    
    return {
        'passed': len(checks_passed),
        'failed': len(issues),
        'checks_passed': checks_passed,
        'issues': issues
    }


def validate_database_columns(loader, sample: Dict) -> Dict:
    """Validate that database columns match schema db_name fields."""
    schema = sample.get('table_schema', {})
    table_name = schema.get('name', '')
    
    issues = []
    checks_passed = []
    
    try:
        # Get database connection
        db_conn = loader.get_database_connection('dev')
        cursor = db_conn.cursor()
        
        # Get actual columns from database
        cursor.execute(f"PRAGMA table_info({table_name})")
        db_columns = [row[1] for row in cursor.fetchall()]  # Column name is index 1
        
        # Get schema columns
        schema_columns = schema.get('columns', [])
        schema_db_names = [col.get('db_name') for col in schema_columns if 'db_name' in col]
        
        # Check if all schema db_names exist in database
        missing_in_db = [name for name in schema_db_names if name not in db_columns]
        if not missing_in_db:
            checks_passed.append("All schema db_name columns exist in database")
        else:
            issues.append(f"Schema db_name columns not found in database: {missing_in_db}")
        
        # Check if database columns match expected format
        expected_format = all(col.startswith('col') and col[3:].isdigit() for col in db_columns)
        if expected_format:
            checks_passed.append("Database columns use colX format")
        else:
            issues.append(f"Database columns don't use colX format: {db_columns}")
        
        db_conn.close()
        
    except Exception as e:
        issues.append(f"Database validation error: {e}")
    
    return {
        'passed': len(checks_passed),
        'failed': len(issues),
        'checks_passed': checks_passed,
        'issues': issues
    }


def validate_prompt_formatting(sample: Dict) -> Dict:
    """Validate that prompt includes correct column name instructions."""
    schema = sample.get('table_schema', {})
    
    issues = []
    checks_passed = []
    
    # Generate prompt (no API call, just formatting)
    generator = GPT4SQLGenerator()
    formatted_schema = generator._format_schema(schema)
    
    # Check for WikiSQL_VALUE specific instructions
    if schema.get('database_name') == 'wikisql_value':
        if 'col0' in formatted_schema or 'col1' in formatted_schema:
            checks_passed.append("Prompt includes colX column names")
        else:
            issues.append("Prompt missing colX column names")
        
        if 'database column names' in formatted_schema.lower() or 'use database column names' in formatted_schema.lower():
            checks_passed.append("Prompt includes instruction to use database column names")
        else:
            issues.append("Prompt missing instruction to use database column names")
        
        # Check for column mapping
        if 'represents:' in formatted_schema.lower() or 'mapping' in formatted_schema.lower():
            checks_passed.append("Prompt includes column mapping information")
        else:
            issues.append("Prompt missing column mapping information")
    
    return {
        'passed': len(checks_passed),
        'failed': len(issues),
        'checks_passed': checks_passed,
        'issues': issues,
        'formatted_schema_preview': formatted_schema[:500] if formatted_schema else None
    }


def validate_spider_schema(sample: Dict) -> Dict:
    """Validate Spider schema structure (should use human-readable names)."""
    schema = sample.get('table_schema', {})
    issues = []
    checks_passed = []
    
    # Spider should NOT have database_name = 'wikisql_value'
    if schema.get('database_name') != 'wikisql_value':
        checks_passed.append("Spider schema correctly identified (not WikiSQL_VALUE)")
    else:
        issues.append("Spider schema incorrectly marked as WikiSQL_VALUE")
    
    # Spider should use human-readable column names
    columns = schema.get('columns', [])
    if columns:
        # Check if columns have human-readable names (not just colX)
        has_readable_names = any(
            col.get('name') and 
            not (col.get('name').startswith('col') and col.get('name')[3:].isdigit())
            for col in columns
        )
        if has_readable_names:
            checks_passed.append("Spider uses human-readable column names")
        else:
            issues.append("Spider columns appear to use colX format (should use readable names)")
    
    return {
        'passed': len(checks_passed),
        'failed': len(issues),
        'checks_passed': checks_passed,
        'issues': issues
    }


def main():
    """Run validation tests."""
    print("=" * 70)
    print("Column Name Mapping Validation")
    print("=" * 70)
    print("\nNOTE: This script does NOT make API calls - safe for testing!")
    print("=" * 70)
    
    # Test WikiSQL_VALUE
    print("\n[TEST 1] WikiSQL_VALUE Schema Validation")
    print("-" * 70)
    try:
        loader = create_loader('wikisql')
        samples = loader.get_sample('dev', n=5)
        
        total_passed = 0
        total_failed = 0
        
        for i, sample in enumerate(samples, 1):
            print(f"\n--- Sample {i} ---")
            question = sample.get('query', {}).get('question', 'N/A')
            print(f"Question: {question[:60]}...")
            
            # Schema validation
            schema_result = validate_wikisql_schema(sample)
            print(f"Schema checks: {schema_result['passed']} passed, {schema_result['failed']} failed")
            if schema_result['issues']:
                for issue in schema_result['issues']:
                    print(f"  [ISSUE] {issue}")
            
            # Database validation
            db_result = validate_database_columns(loader, sample)
            print(f"Database checks: {db_result['passed']} passed, {db_result['failed']} failed")
            if db_result['issues']:
                for issue in db_result['issues']:
                    print(f"  [ISSUE] {issue}")
            
            # Prompt validation
            prompt_result = validate_prompt_formatting(sample)
            print(f"Prompt checks: {prompt_result['passed']} passed, {prompt_result['failed']} failed")
            if prompt_result['issues']:
                for issue in prompt_result['issues']:
                    print(f"  [ISSUE] {issue}")
            
            total_passed += schema_result['passed'] + db_result['passed'] + prompt_result['passed']
            total_failed += schema_result['failed'] + db_result['failed'] + prompt_result['failed']
        
        print(f"\n--- WikiSQL_VALUE Summary ---")
        print(f"Total checks passed: {total_passed}")
        print(f"Total checks failed: {total_failed}")
        
    except Exception as e:
        print(f"[ERROR] WikiSQL_VALUE validation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Spider
    print("\n\n[TEST 2] Spider Schema Validation")
    print("-" * 70)
    try:
        loader = create_loader('spider')
        samples = loader.get_sample('dev', n=3)
        
        total_passed = 0
        total_failed = 0
        
        for i, sample in enumerate(samples, 1):
            print(f"\n--- Sample {i} ---")
            question = sample.get('query', {}).get('question', 'N/A')
            print(f"Question: {question[:60]}...")
            
            # Schema validation
            schema_result = validate_spider_schema(sample)
            print(f"Schema checks: {schema_result['passed']} passed, {schema_result['failed']} failed")
            if schema_result['issues']:
                for issue in schema_result['issues']:
                    print(f"  [ISSUE] {issue}")
            
            total_passed += schema_result['passed']
            total_failed += schema_result['failed']
        
        print(f"\n--- Spider Summary ---")
        print(f"Total checks passed: {total_passed}")
        print(f"Total checks failed: {total_failed}")
        
    except Exception as e:
        print(f"[ERROR] Spider validation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Validation Complete!")
    print("=" * 70)
    print("\nNOTE: This script validates structure only.")
    print("For actual SQL generation testing, use test_column_name_fix.py")
    print("(which requires API calls)")


if __name__ == "__main__":
    main()
