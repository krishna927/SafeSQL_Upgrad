"""Run FULL evaluation using Model 2 (LLaMA-3, FREE) on complete datasets.

This script runs evaluation on the ENTIRE development sets using Model 2 (LLaMA-3),
which is FREE via Groq API or can run locally with HuggingFace.

Cost: $0 (FREE)
Time: Similar to GPT-4 but FREE
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.run_models_spider_bird import main as run_evaluation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FULL evaluation using Model 2 (LLaMA-3, FREE)")
    parser.add_argument("--spider_only", action="store_true", help="Run only on Spider dataset")
    parser.add_argument("--wikisql_only", action="store_true", help="Run only on WikiSQL_VALUE dataset")
    parser.add_argument("--provider", type=str, default="groq", choices=["groq", "huggingface"], 
                       help="Model 2 provider: 'groq' (free API, recommended) or 'huggingface' (local, requires GPU)")
    parser.add_argument("--confirm", action="store_true", help="Confirm you want to run full evaluation")
    
    args = parser.parse_args()
    
    # Check dataset sizes
    print("=" * 70)
    print("FULL EVALUATION - Model 2 (LLaMA-3, FREE)")
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
    print("✅ Model 2 (LLaMA-3) - FREE Evaluation")
    print("=" * 70)
    print(f"Provider: {args.provider.upper()}")
    if args.provider == "groq":
        print("✅ FREE API (Groq)")
        print("   Get free API key at: https://console.groq.com/")
        print("   Set GROQ_API_KEY environment variable")
    else:
        print("✅ Local inference (HuggingFace)")
        print("   Requires GPU for reasonable speed")
        print("   Will download model (~15GB) on first run")
    
    print("\nThis will evaluate on the COMPLETE dataset (not samples).")
    print("Estimated time: 8-16 hours (similar to GPT-4)")
    print("Estimated cost: $0 (FREE!)")
    
    if not args.confirm:
        print("\n⚠️  To proceed, run with --confirm flag:")
        print("  python scripts/run_full_evaluation_model2.py --spider_only --confirm")
        print("=" * 70)
        sys.exit(1)
    
    # Modify sys.argv to pass to the evaluation script
    import sys
    original_argv = sys.argv[:]
    sys.argv = ['run_models_spider_bird.py', '--model2', '--model2_provider', args.provider]
    
    if args.spider_only:
        sys.argv.append('--spider_only')
    if args.wikisql_only:
        sys.argv.append('--wikisql_only')
    
    # Use very large number to get all samples
    sys.argv.extend(['--n_samples', '999999'])
    
    print(f"\n🚀 Starting FULL evaluation with Model 2 (LLaMA-3)")
    print(f"   Provider: {args.provider}")
    print(f"   n_samples: 999999 (will use all available queries)")
    print("=" * 70)
    
    # Run the evaluation
    run_evaluation()
