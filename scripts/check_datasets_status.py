"""Check status of all datasets - integrated, downloaded, and working."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.dataset_factory import create_loader

print("=" * 70)
print("DATASET STATUS SUMMARY")
print("=" * 70)

datasets_info = {
    'wikisql': {
        'name': 'WikiSQL_VALUE',
        'loader': True,
        'expected_files': ['dev.jsonl', 'train.jsonl'],
        'location': 'data/datasets/wikisql_value'
    },
    'spider': {
        'name': 'Spider',
        'loader': True,
        'expected_files': ['dev.json', 'train_spider.json', 'tables.json', 'database/'],
        'location': 'data/datasets/spider'
    },
    'bird': {
        'name': 'BIRD',
        'loader': True,
        'expected_files': ['train/train.json', 'dev/dev.json', 'dev_databases/'],
        'location': 'data/datasets/bird'
    }
}

results = {}

for ds_key, ds_info in datasets_info.items():
    print(f"\n{ds_info['name']}:")
    print("-" * 70)
    
    # Check if loader exists
    loader_status = "[OK] Loader Implemented" if ds_info['loader'] else "[MISSING] Loader Missing"
    print(f"  Loader: {loader_status}")
    
    # Check if dataset directory exists
    ds_path = project_root / ds_info['location']
    dir_exists = ds_path.exists()
    print(f"  Directory: {'[OK] Found' if dir_exists else '[MISSING] Not Found'}")
    
    # Check files
    files_status = {}
    if dir_exists:
        for file_pattern in ds_info['expected_files']:
            if '/' in file_pattern:
                # It's a path
                file_path = ds_path / file_pattern
                exists = file_path.exists()
            else:
                # It's a file or directory in root
                file_path = ds_path / file_pattern
                exists = file_path.exists()
            
            files_status[file_pattern] = exists
            status_icon = "[OK]" if exists else "[MISSING]"
            print(f"  {file_pattern}: {status_icon}")
    
    # Try to load dataset
    can_load = False
    if ds_info['loader']:
        try:
            loader = create_loader(ds_key)
            can_load = True
            print(f"  Loader Test: [OK] Can create loader")
            
            # Try to load queries
            try:
                queries = loader.load_queries('dev', n=1) if hasattr(loader, 'load_queries') else []
                if queries or not hasattr(loader, 'load_queries'):
                    print(f"  Query Loading: [OK] Working")
                else:
                    print(f"  Query Loading: [WARN] No queries loaded")
            except Exception as e:
                print(f"  Query Loading: [ERROR] Error - {str(e)[:50]}")
        except Exception as e:
            print(f"  Loader Test: [ERROR] Error - {str(e)[:50]}")
    
    # Determine overall status
    all_files = all(files_status.values()) if files_status else False
    if can_load and all_files:
        overall_status = "[OK] FULLY INTEGRATED"
    elif can_load and not all_files:
        overall_status = "[PARTIAL] PARTIALLY INTEGRATED"
    elif ds_info['loader']:
        overall_status = "[READY] LOADER READY (Data Missing)"
    else:
        overall_status = "[MISSING] NOT INTEGRATED"
    
    results[ds_key] = {
        'status': overall_status,
        'loader': ds_info['loader'],
        'files': files_status,
        'can_load': can_load
    }
    
    print(f"  Overall Status: {overall_status}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

fully_integrated = [k for k, v in results.items() if "[OK]" in v['status']]
partially_integrated = [k for k, v in results.items() if "[PARTIAL]" in v['status']]
loader_ready = [k for k, v in results.items() if "[READY]" in v['status']]
not_integrated = [k for k, v in results.items() if "[MISSING]" in v['status']]

print(f"\n[OK] Fully Integrated: {len(fully_integrated)}")
for ds in fully_integrated:
    print(f"   - {datasets_info[ds]['name']}")

print(f"\n[PARTIAL] Partially Integrated: {len(partially_integrated)}")
for ds in partially_integrated:
    print(f"   - {datasets_info[ds]['name']}")

print(f"\n[READY] Loader Ready (Data Missing): {len(loader_ready)}")
for ds in loader_ready:
    print(f"   - {datasets_info[ds]['name']}")

print(f"\n[MISSING] Not Integrated: {len(not_integrated)}")
for ds in not_integrated:
    print(f"   - {datasets_info[ds]['name']}")

print(f"\nTotal Datasets: {len(results)}")
print(f"Working Datasets: {len(fully_integrated) + len(partially_integrated)}")

print("\n" + "=" * 70)
