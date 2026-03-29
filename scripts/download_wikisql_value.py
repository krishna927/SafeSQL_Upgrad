"""Download and explore WikiSQL_VALUE dataset."""

import os
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from datasets import load_dataset
    from huggingface_hub import snapshot_download
    import zipfile
except ImportError:
    print("ERROR: Required libraries not found.")
    print("Install with: pip install datasets huggingface_hub")
    sys.exit(1)


def download_wikisql_value():
    """Download WikiSQL_VALUE dataset."""
    print("=" * 60)
    print("Downloading WikiSQL_VALUE Dataset")
    print("=" * 60)
    
    base_dir = project_root / "data" / "datasets"
    wikisql_dir = base_dir / "wikisql_value"
    wikisql_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {wikisql_dir}")
    print("\nAttempting to load dataset...")
    
    try:
        # Try loading directly - the dataset should be auto-converted to Parquet
        print("Loading dataset (this may take a few minutes)...")
        print("Note: If this fails, the dataset may need to be loaded from Parquet files directly.")
        
        # Try loading with data_files parameter to force Parquet loading
        try:
            dataset = load_dataset(
                "SALT-NLP/wikisql_VALUE",
                token=os.getenv("HUGGINGFACE_TOKEN")
            )
        except RuntimeError as e:
            if "Dataset scripts are no longer supported" in str(e):
                print("\nDataset uses legacy script format. Downloading files directly...")
                
                # Download entire repository snapshot
                repo_id = "SALT-NLP/wikisql_VALUE"
                print(f"Downloading snapshot from {repo_id}...")
                
                cache_dir = snapshot_download(
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=os.getenv("HUGGINGFACE_TOKEN"),
                    local_dir=str(wikisql_dir),
                    local_dir_use_symlinks=False
                )
                
                print(f"Files downloaded to: {cache_dir}")
                
                # Check for data.zip file
                zip_file = Path(cache_dir) / "data.zip"
                if zip_file.exists():
                    print(f"\nFound data.zip file. Extracting...")
                    extract_dir = Path(cache_dir) / "extracted"
                    extract_dir.mkdir(exist_ok=True)
                    
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    print(f"Extracted to: {extract_dir}")
                    
                    # Look for Parquet files in extracted directory
                    parquet_files = list(extract_dir.rglob("*.parquet"))
                    print(f"Found {len(parquet_files)} Parquet files after extraction")
                    
                    if parquet_files:
                        # Group by split if possible
                        data_files = {}
                        for pfile in parquet_files:
                            # Try to infer split from path
                            path_str = str(pfile).lower()
                            if "train" in path_str:
                                if "train" not in data_files:
                                    data_files["train"] = []
                                data_files["train"].append(str(pfile))
                            elif "validation" in path_str or "val" in path_str:
                                if "validation" not in data_files:
                                    data_files["validation"] = []
                                data_files["validation"].append(str(pfile))
                            elif "test" in path_str:
                                if "test" not in data_files:
                                    data_files["test"] = []
                                data_files["test"].append(str(pfile))
                        
                        if data_files:
                            print(f"Loading splits: {list(data_files.keys())}")
                            dataset = load_dataset("parquet", data_files=data_files)
                        else:
                            # Load all files as one split
                            print("Loading all files as single dataset...")
                            dataset = load_dataset("parquet", data_files=[str(f) for f in parquet_files])
                    else:
                        # Check for JSONL files (JSON Lines format)
                        jsonl_files = list(extract_dir.rglob("*.jsonl"))
                        if jsonl_files:
                            print(f"Found {len(jsonl_files)} JSONL files. Loading...")
                            
                            # Group files by split/subset
                            data_files = {}
                            for jsonl_file in jsonl_files:
                                filename = jsonl_file.name.lower()
                                # Skip table files for now
                                if "tables" in filename:
                                    continue
                                
                                # Main dev file
                                if filename == "dev.jsonl":
                                    data_files["dev"] = str(jsonl_file)
                                # Subset files (dev_AppE.jsonl, etc.)
                                elif filename.startswith("dev_"):
                                    subset = filename.replace("dev_", "").replace(".jsonl", "")
                                    data_files[f"dev_{subset}"] = str(jsonl_file)
                                elif "train" in filename:
                                    if "train" not in data_files:
                                        data_files["train"] = []
                                    data_files["train"].append(str(jsonl_file))
                                elif "test" in filename:
                                    if "test" not in data_files:
                                        data_files["test"] = []
                                    data_files["test"].append(str(jsonl_file))
                            
                            if data_files:
                                print(f"Loading splits: {list(data_files.keys())}")
                                # JSONL files need lines=True
                                dataset = load_dataset("json", data_files=data_files, lines=True)
                            else:
                                # Load all JSONL files
                                dataset = load_dataset("json", data_files=[str(f) for f in jsonl_files if "tables" not in f.name], lines=True)
                        else:
                            # Check for regular JSON files
                            json_files = list(extract_dir.rglob("*.json"))
                            if json_files:
                                print(f"Found {len(json_files)} JSON files. Loading...")
                                dataset = load_dataset("json", data_files=[str(f) for f in json_files])
                            else:
                                raise RuntimeError(f"No Parquet, JSONL, or JSON files found. Files in extract_dir: {list(extract_dir.rglob('*'))[:10]}")
                else:
                    # Try to find Parquet files directly
                    parquet_files = list(Path(cache_dir).glob("**/*.parquet"))
                    if parquet_files:
                        dataset = load_dataset("parquet", data_files=[str(f) for f in parquet_files])
                    else:
                        raise RuntimeError(f"No data.zip or Parquet files found. Files: {list(Path(cache_dir).iterdir())}")
        
        print("\nDataset loaded successfully!")
        print(f"Dataset splits: {list(dataset.keys())}")
        
        # Save to disk
        print(f"\nSaving dataset to {wikisql_dir}...")
        dataset.save_to_disk(str(wikisql_dir))
        print(f"Status: Dataset saved to {wikisql_dir}")
        
        # Print basic info
        print("\n" + "=" * 60)
        print("Dataset Information")
        print("=" * 60)
        
        for split_name, split_data in dataset.items():
            print(f"\nSplit: {split_name}")
            print(f"  Number of examples: {len(split_data)}")
            print(f"  Features: {list(split_data.features.keys())}")
            
            # Show first example
            if len(split_data) > 0:
                print(f"\n  First example:")
                example = split_data[0]
                for key, value in example.items():
                    if isinstance(value, dict):
                        print(f"    {key}: (dict with keys: {list(value.keys())})")
                    elif isinstance(value, list):
                        print(f"    {key}: (list with {len(value)} items)")
                    elif isinstance(value, str) and len(value) > 100:
                        print(f"    {key}: {value[:100]}...")
                    else:
                        print(f"    {key}: {value}")
        
        # Save a sample to JSON for easy inspection
        sample_file = wikisql_dir / "sample.json"
        print(f"\nSaving sample to {sample_file}...")
        sample_data = {}
        for split_name, split_data in dataset.items():
            sample_data[split_name] = {
                "num_examples": len(split_data),
                "features": list(split_data.features.keys()),
                "first_example": split_data[0] if len(split_data) > 0 else None
            }
        
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Status: Sample saved to {sample_file}")
        
        return True
        
    except Exception as e:
        print(f"\nError: Failed to download WikiSQL_VALUE: {e}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_wikisql_value()
    sys.exit(0 if success else 1)
