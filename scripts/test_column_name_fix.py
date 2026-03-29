"""
Test script to verify WikiSQL_VALUE column name mapping fix.
Tests that GPT-4 generates SQL with database column names (col0, col1, etc.)
instead of human-readable names.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.dataset_factory import create_loader
from src.models.gpt4_generator import GPT4SQLGenerator
from src.evaluation.evaluator import SafeSQLEvaluator
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_schema_column_mapping():
    """Test that schema includes database column names."""
    print("=" * 70)
    print("TEST 1: Schema Column Name Mapping")
    print("=" * 70)
    
    loader = create_loader("wikisql_value")
    samples = loader.get_sample("dev", n=3)
    
    if not samples:
        print("❌ ERROR: No samples loaded")
        return False
    
    print(f"\n[OK] Loaded {len(samples)} samples")
    
    for i, sample in enumerate(samples, 1):
        schema = sample.get('table_schema', {})
        columns = schema.get('columns', [])
        
        print(f"\n--- Sample {i} ---")
        print(f"Table: {schema.get('name', 'N/A')}")
        print(f"Database: {schema.get('database_name', 'N/A')}")
        print(f"Columns ({len(columns)}):")
        
        has_db_names = False
        for col in columns[:5]:  # Show first 5 columns
            name = col.get('name', 'N/A')
            db_name = col.get('db_name', 'N/A')
            if db_name != 'N/A':
                has_db_names = True
            print(f"  - {name} -> {db_name} ({col.get('type', 'N/A')})")
        
        if has_db_names:
            print("[OK] Schema includes database column names (db_name field)")
        else:
            print("[ERROR] Schema missing database column names")
            return False
    
    return True

def test_prompt_formatting():
    """Test that GPT-4 prompt includes database column names."""
    print("\n" + "=" * 70)
    print("TEST 2: GPT-4 Prompt Formatting")
    print("=" * 70)
    
    loader = create_loader("wikisql_value")
    samples = loader.get_sample("dev", n=1)
    
    if not samples:
        print("❌ ERROR: No samples loaded")
        return False
    
    sample = samples[0]
    schema = sample.get('table_schema', {})
    question = sample.get('query', {}).get('question', '')
    
    generator = GPT4SQLGenerator()
    
    # Build prompt (without actually calling API)
    prompt = generator._build_prompt(question, schema)
    formatted_schema = generator._format_schema(schema)
    
    print("\n--- Schema Formatting ---")
    print(formatted_schema)
    
    # Check if prompt includes database column names
    if 'col0' in formatted_schema or 'col1' in formatted_schema:
        print("\n[OK] Prompt includes database column names (col0, col1, etc.)")
        return True
    else:
        print("\n[ERROR] Prompt missing database column names")
        return False

def test_sql_generation():
    """Test that GPT-4 generates SQL with database column names."""
    print("\n" + "=" * 70)
    print("TEST 3: SQL Generation with Database Column Names")
    print("=" * 70)
    
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("[SKIP] OPENAI_API_KEY not set")
        print("   Set it to test actual SQL generation")
        return None
    
    loader = create_loader("wikisql_value")
    samples = loader.get_sample("dev", n=5)
    
    if not samples:
        print("[ERROR] No samples loaded")
        return False
    
    generator = GPT4SQLGenerator()
    evaluator = SafeSQLEvaluator()
    
    results = []
    correct_count = 0
    
    for i, sample in enumerate(samples, 1):
        schema = sample.get('table_schema', {})
        question = sample.get('query', {}).get('question', '')
        gold_sql = sample.get('sql_string', '')
        
        if not gold_sql:
            print(f"\n[SKIP] Sample {i}: No gold SQL available")
            continue
        
        print(f"\n--- Sample {i} ---")
        print(f"Question: {question[:80]}...")
        
        try:
            # Generate SQL
            generated_sql = generator.generate(question, schema)
            print(f"Generated: {generated_sql[:100]}...")
            print(f"Gold:      {gold_sql[:100]}...")
            
            # Check if uses database column names
            uses_db_names = 'col0' in generated_sql or 'col1' in generated_sql or 'col2' in generated_sql
            uses_human_names = '"Player"' in generated_sql or '"Position"' in generated_sql or '"School/Club Team"' in generated_sql
            
            if uses_db_names:
                print("[OK] Uses database column names (col0, col1, etc.)")
                correct_count += 1
            elif uses_human_names:
                print("[ERROR] Still using human-readable names")
            else:
                print("[WARN] Unclear - check manually")
            
            results.append({
                'question': question,
                'generated': generated_sql,
                'gold': gold_sql,
                'uses_db_names': uses_db_names
            })
            
        except Exception as e:
            print(f"[ERROR] Error generating SQL: {e}")
            continue
    
    print(f"\n--- Summary ---")
    print(f"Generated SQL for {len(results)} samples")
    print(f"Using database column names: {correct_count}/{len(results)}")
    
    if correct_count == len(results) and len(results) > 0:
        print("[SUCCESS] All SQL uses database column names!")
        return True
    elif correct_count > 0:
        print(f"[PARTIAL] Partial success: {correct_count}/{len(results)}")
        return None
    else:
        print("[FAIL] No SQL uses database column names")
        return False

def test_execution_accuracy():
    """Test execution accuracy improvement."""
    print("\n" + "=" * 70)
    print("TEST 4: Execution Accuracy Test")
    print("=" * 70)
    
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("[SKIP] OPENAI_API_KEY not set")
        return None
    
    loader = create_loader("wikisql_value")
    generator = GPT4SQLGenerator()
    evaluator = SafeSQLEvaluator()
    
    samples = loader.get_sample("dev", n=10)
    
    if not samples:
        print("[ERROR] No samples loaded")
        return False
    
    print(f"\nTesting {len(samples)} samples...")
    
    correct = 0
    total = 0
    
    for i, sample in enumerate(samples, 1):
        schema = sample.get('table_schema', {})
        question = sample.get('query', {}).get('question', '')
        gold_sql = sample.get('sql_string', '')
        
        if not gold_sql:
            continue
        
        try:
            # Generate SQL
            generated_sql = generator.generate(question, schema)
            
            # Get database connection
            db_conn = loader.get_database_connection("dev")
            
            # Execute both queries
            try:
                cursor = db_conn.cursor()
                cursor.execute(generated_sql)
                gen_results = cursor.fetchall()
                
                cursor.execute(gold_sql)
                gold_results = cursor.fetchall()
                
                # Compare results
                if gen_results == gold_results:
                    correct += 1
                    status = "[OK]"
                else:
                    status = "[FAIL]"
                
                total += 1
                print(f"{status} Sample {i}: {'CORRECT' if gen_results == gold_results else 'WRONG'}")
                
            except Exception as e:
                print(f"[ERROR] Sample {i}: Execution error - {str(e)[:50]}")
                total += 1
            
            db_conn.close()
            
        except Exception as e:
            print(f"[ERROR] Sample {i}: Generation error - {e}")
            continue
    
    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n--- Results ---")
        print(f"Execution Accuracy: {accuracy:.1f}% ({correct}/{total})")
        
        if accuracy >= 85:
            print("[SUCCESS] Target achieved! (85%+)")
            return True
        elif accuracy >= 60:
            print(f"[PARTIAL] Improved but below target (current: {accuracy:.1f}%, target: 85%+)")
            return None
        else:
            print("[FAIL] Below expected improvement")
            return False
    else:
        print("[ERROR] No valid tests completed")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("WIKISQL_VALUE COLUMN NAME MAPPING FIX - VERIFICATION TESTS")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Schema mapping
    results['schema'] = test_schema_column_mapping()
    
    # Test 2: Prompt formatting
    results['prompt'] = test_prompt_formatting()
    
    # Test 3: SQL generation (requires API key)
    results['generation'] = test_sql_generation()
    
    # Test 4: Execution accuracy (requires API key)
    results['accuracy'] = test_execution_accuracy()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, result in results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"{test_name.upper():15} {status}")
    
    print("\n" + "=" * 70)
    
    if all(r is True for r in results.values() if r is not None):
        print("[SUCCESS] ALL TESTS PASSED!")
    elif any(r is True for r in results.values()):
        print("[PARTIAL] SOME TESTS PASSED - Review results above")
    else:
        print("[FAIL] TESTS FAILED - Review errors above")

if __name__ == "__main__":
    main()
