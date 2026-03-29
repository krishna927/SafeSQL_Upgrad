"""Quick test to verify Spider loader works with downloaded dataset."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.spider_loader import SpiderLoader

print("=" * 70)
print("Testing Spider Dataset Loader")
print("=" * 70)

try:
    loader = SpiderLoader()
    print("\n[OK] Spider loader initialized successfully")
    
    # Test loading queries
    queries = loader.load_queries("dev")
    print(f"[OK] Loaded {len(queries)} dev queries")
    
    if queries:
        first_query = queries[0]
        print(f"\nFirst query example:")
        print(f"  Question: {first_query['question'][:60]}...")
        print(f"  DB ID: {first_query.get('db_id', 'N/A')}")
        sql_val = first_query.get('sql') or first_query.get('query', 'N/A')
        sql_str = str(sql_val)[:80] if sql_val else 'N/A'
        print(f"  SQL: {sql_str}...")
    
    # Test loading tables
    tables = loader.load_tables()
    print(f"\n[OK] Loaded {len(tables)} database schemas")
    
    if tables:
        first_db_id = list(tables.keys())[0]
        schema = tables[first_db_id]
        print(f"\nFirst database schema:")
        print(f"  DB ID: {first_db_id}")
        print(f"  Tables: {schema.get('table_names', [])[:5]}")
        print(f"  Columns: {len(schema.get('column_names', []))} columns")
    
    # Test getting sample
    samples = loader.get_sample("dev", n=3)
    print(f"\n[OK] Got {len(samples)} samples")
    
    # Test database connection
    if samples:
        db_id = samples[0].get('db_id')
        if db_id:
            db_path = loader.get_database_path(db_id)
            if db_path:
                print(f"\n[OK] Database path found for {db_id}: {db_path}")
            else:
                print(f"\n[WARN] Database path not found for {db_id}")
    
    print("\n" + "=" * 70)
    print("Spider Dataset Loader Test: SUCCESS")
    print("=" * 70)
    
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
