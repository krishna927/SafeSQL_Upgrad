"""Run FULL evaluation on complete datasets.

This script runs evaluation on the ENTIRE development/test sets, not just samples.
Use with caution - this will make many API calls and incur costs.
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.run_models_spider_bird import main as run_evaluation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FULL evaluation on complete datasets")
    parser.add_argument("--spider_only", action="store_true", help="Run only on Spider dataset")
    parser.add_argument("--wikisql_only", action="store_true", help="Run only on WikiSQL_VALUE dataset")
    parser.add_argument("--use_test_set", action="store_true", help="Use test sets instead of dev sets")
    parser.add_argument("--confirm", action="store_true", help="Confirm you understand this will incur API costs")
    
    args = parser.parse_args()
    
    # Check dataset sizes
    print("=" * 70)
    print("FULL EVALUATION - Complete Dataset")
    print("=" * 70)
    
    try:
        import json
        spider_path = project_root / "data" / "datasets" / "spider" / "dev.json"
        if spider_path.exists():
            spider_data = json.load(open(spider_path))
            spider_count = len(spider_data)
            print(f"\nSpider dev set: {spider_count} queries")
        
        wikisql_path = project_root / "data" / "datasets" / "wikisql_value" / "extracted" / "data" / "dev.jsonl"
        if wikisql_path.exists():
            with open(wikisql_path, 'r') as f:
                wikisql_count = sum(1 for _ in f)
            print(f"WikiSQL_VALUE dev set: {wikisql_count} queries")
    except Exception as e:
        print(f"Could not determine dataset sizes: {e}")
    
    print("\n" + "=" * 70)
    print("⚠️  WARNING: FULL EVALUATION")
    print("=" * 70)
    print("This will evaluate on the COMPLETE dataset, not samples.")
    print("Estimated costs: $100-500+ (depending on query complexity)")
    print("Estimated time: 10-20+ hours")
    print("\nTo proceed, run with --confirm flag:")
    print("  python scripts/run_full_evaluation.py --spider_only --confirm")
    print("=" * 70)
    
    if not args.confirm:
        print("\n❌ Evaluation cancelled. Use --confirm to proceed.")
        sys.exit(1)
    
    # Determine n_samples - use a very large number to get all samples
    # The script will be limited by actual dataset size
    n_samples = 999999  # Effectively unlimited
    
    # Modify sys.argv to pass to the evaluation script
    import sys
    original_argv = sys.argv[:]
    sys.argv = ['run_models_spider_bird.py']
    if args.spider_only:
        sys.argv.append('--spider_only')
    if args.wikisql_only:
        sys.argv.append('--wikisql_only')
    sys.argv.extend(['--n_samples', str(n_samples)])
    
    print(f"\n🚀 Starting FULL evaluation with n_samples={n_samples} (will use all available queries)")
    print("=" * 70)
    
    # Run the evaluation
    run_evaluation()
