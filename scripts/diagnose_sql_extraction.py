"""Diagnostic script to check SQL extraction and execution for both datasets."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.dataset_factory import create_loader
from src.data.preprocessors.schema_serializer_factory import create_serializer

def diagnose_dataset(dataset_name: str):
    """Diagnose SQL extraction for a dataset."""
    print("\n" + "=" * 70)
    print(f"Diagnosing {dataset_name.upper()}")
    print("=" * 70)
    
    loader = create_loader(dataset_name)
    serializer = create_serializer(dataset_name)
    
    # Get one sample
    samples = loader.get_sample("dev", n=1)
    if not samples:
        print(f"[ERROR] No samples loaded")
        return
    
    sample = samples[0]
    print(f"\nSample keys: {list(sample.keys())}")
    
    # Check query structure
    if 'query' in sample:
        query_data = sample['query']
        print(f"\nQuery keys: {list(query_data.keys())}")
        print(f"Question: {query_data.get('question', 'N/A')[:80]}")
        print(f"Has 'query' field: {'query' in query_data}")
        print(f"Has 'sql' field: {'sql' in query_data}")
        print(f"Has 'SQL' field: {'SQL' in query_data}")
        
        if 'query' in query_data:
            sql_val = query_data['query']
            print(f"  'query' type: {type(sql_val)}")
            print(f"  'query' value (first 100 chars): {str(sql_val)[:100]}")
        
        if 'sql' in query_data:
            sql_val = query_data['sql']
            print(f"  'sql' type: {type(sql_val)}")
            if isinstance(sql_val, dict):
                print(f"  'sql' dict keys: {list(sql_val.keys())}")
            else:
                print(f"  'sql' value (first 100 chars): {str(sql_val)[:100]}")
    
    # Check for sql_string
    if 'sql_string' in sample:
        print(f"\nHas 'sql_string' field: True")
        print(f"sql_string (first 100 chars): {sample['sql_string'][:100] if sample['sql_string'] else 'None'}")
    
    # Try to extract gold SQL
    print("\n--- Testing Gold SQL Extraction ---")
    try:
        # Method 1: Check sql_string
        if 'sql_string' in sample and sample['sql_string']:
            gold_sql = sample['sql_string']
            print(f"[OK] Method 1 (sql_string): {gold_sql[:100]}")
        else:
            # Method 2: Convert from dict
            gold_sql_dict = sample['query'].get('query') or sample['query'].get('sql') or sample['query'].get('SQL', '')
            schema_data = sample.get('table_schema') or sample.get('database_schema', {})
            gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
            print(f"[OK] Method 2 (convert_sql_to_string): {gold_sql[:100]}")
        
        print(f"\nGold SQL: {gold_sql}")
        
        # Check database connection
        print("\n--- Testing Database Connection ---")
        db_id = sample.get('db_id') or sample.get('table_id')
        print(f"db_id/table_id: {db_id}")
        
        if hasattr(loader, 'get_database_connection'):
            try:
                if db_id:
                    db_conn = loader.get_database_connection(db_id)
                    print(f"[OK] Database connection via db_id: {db_id}")
                else:
                    db_conn = loader.get_database_connection("dev")
                    print(f"[OK] Database connection via split: dev")
                
                # Try executing gold SQL
                try:
                    cursor = db_conn.cursor()
                    cursor.execute(gold_sql)
                    results = cursor.fetchall()
                    print(f"[OK] Gold SQL executed successfully, returned {len(results)} rows")
                    if results:
                        print(f"  First row: {results[0]}")
                except Exception as e:
                    print(f"[ERROR] Gold SQL execution failed: {e}")
                
                db_conn.close()
            except Exception as e:
                print(f"[ERROR] Database connection failed: {e}")
        else:
            print("[WARN] Loader doesn't have get_database_connection method")
            
    except Exception as e:
        print(f"[ERROR] Gold SQL extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    diagnose_dataset("spider")
    diagnose_dataset("wikisql")
