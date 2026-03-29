"""Explore WikiSQL_VALUE dataset from downloaded files."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def explore_dataset():
    """Load and explore the WikiSQL_VALUE dataset."""
    data_dir = project_root / "data" / "datasets" / "wikisql_value" / "extracted" / "data"
    
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        print("Please run download_wikisql_value.py first to download and extract the dataset.")
        return False
    
    print("=" * 60)
    print("WikiSQL_VALUE Dataset Exploration")
    print("=" * 60)
    
    # Find all JSONL files
    jsonl_files = list(data_dir.glob("*.jsonl"))
    jsonl_files = [f for f in jsonl_files if "tables" not in f.name]
    
    print(f"\nFound {len(jsonl_files)} JSONL files:")
    for f in sorted(jsonl_files):
        print(f"  - {f.name}")
    
    # Load and explore each file
    datasets = {}
    
    for jsonl_file in sorted(jsonl_files):
        print(f"\n{'='*60}")
        print(f"Loading: {jsonl_file.name}")
        print(f"{'='*60}")
        
        examples = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    example = json.loads(line.strip())
                    examples.append(example)
                except json.JSONDecodeError as e:
                    print(f"  Warning: Error parsing line {line_num}: {e}")
        
        print(f"  Loaded {len(examples)} examples")
        
        if examples:
            print(f"\n  First example structure:")
            first_example = examples[0]
            for key, value in first_example.items():
                if isinstance(value, dict):
                    print(f"    {key}: dict with keys: {list(value.keys())}")
                    # Show nested structure for sql
                    if key == "sql":
                        print(f"      sql structure:")
                        for sql_key, sql_val in value.items():
                            if isinstance(sql_val, list):
                                print(f"        {sql_key}: list[{len(sql_val)}]")
                                if sql_val and isinstance(sql_val[0], dict):
                                    print(f"          First item keys: {list(sql_val[0].keys())}")
                            else:
                                print(f"        {sql_key}: {type(sql_val).__name__}")
                elif isinstance(value, list):
                    print(f"    {key}: list[{len(value)}]")
                    if value and isinstance(value[0], dict):
                        print(f"      First item keys: {list(value[0].keys())}")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"    {key}: str (length: {len(value)}, preview: {value[:100]}...)")
                else:
                    print(f"    {key}: {type(value).__name__} = {value}")
            
            # Show a few more examples of the question field
            print(f"\n  Sample questions (first 5):")
            for i, ex in enumerate(examples[:5], 1):
                question = ex.get('question', 'N/A')
                print(f"    {i}. {question}")
        
        datasets[jsonl_file.stem] = examples
    
    # Summary
    print(f"\n{'='*60}")
    print("Dataset Summary")
    print(f"{'='*60}")
    total_examples = sum(len(examples) for examples in datasets.values())
    print(f"Total examples across all files: {total_examples}")
    print(f"\nBreakdown by file:")
    for name, examples in datasets.items():
        print(f"  {name}: {len(examples)} examples")
    
    # Save a sample for easy inspection
    sample_file = project_root / "data" / "datasets" / "wikisql_value" / "sample_exploration.json"
    print(f"\nSaving sample to: {sample_file}")
    
    sample_data = {
        "summary": {
            "total_files": len(datasets),
            "total_examples": total_examples,
            "files": {name: len(examples) for name, examples in datasets.items()}
        },
        "samples": {}
    }
    
    for name, examples in datasets.items():
        if examples:
            sample_data["samples"][name] = {
                "count": len(examples),
                "first_example": examples[0],
                "sample_questions": [ex.get('question', '') for ex in examples[:5]]
            }
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Status: Sample saved")
    
    return True


if __name__ == "__main__":
    success = explore_dataset()
    sys.exit(0 if success else 1)
