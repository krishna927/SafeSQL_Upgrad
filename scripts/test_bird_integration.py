"""Test script to verify BIRD dataset integration with Models 1 and 3.

This script tests:
- Model 1: GPT-4 + SafeSQL (Guardrails + Verification)
- Model 3: Baseline GPT-4 (without SafeSQL)

on both Spider and BIRD datasets.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env BEFORE importing
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

from src.models.gpt4_generator import GPT4SQLGenerator
from src.guardrails import Guardrails
from src.data.loaders.dataset_factory import create_loader
from src.data.preprocessors.schema_serializer_factory import create_serializer
from src.verification import Verifier
from src.evaluation import SafeSQLEvaluator
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def test_dataset_integration(dataset_name: str, n_samples: int = 3):
    """
    Test dataset integration with Models 1 and 3.
    
    Args:
        dataset_name: Name of dataset ('spider' or 'bird')
        n_samples: Number of samples to test
    """
    print("=" * 70)
    print(f"Testing {dataset_name.upper()} Dataset Integration")
    print("=" * 70)
    
    try:
        # Initialize loader and serializer
        print(f"\n1. Initializing {dataset_name} loader...")
        loader = create_loader(dataset_name)
        serializer = create_serializer(dataset_name)
        print(f"   Status: Loader initialized successfully")
        
        # Load sample queries
        print(f"\n2. Loading sample queries...")
        samples = loader.get_sample("dev", n=n_samples)
        print(f"   Status: Loaded {len(samples)} samples")
        
        if not samples:
            print(f"   Error: No samples loaded. Please check dataset location.")
            return
        
        # Initialize models
        print(f"\n3. Initializing models...")
        generator = GPT4SQLGenerator(config={"model": "gpt-4"})
        guardrails = Guardrails()
        verifier = Verifier(enable_repair=True)
        evaluator = SafeSQLEvaluator()
        print(f"   Status: All models initialized")
        
        # Test Model 3: Baseline GPT-4
        print(f"\n4. Testing Model 3: Baseline GPT-4 (without SafeSQL)...")
        baseline_results = []
        
        for i, sample in enumerate(samples, 1):
            question = sample['query']['question']
            # Handle different SQL field names
            gold_sql_dict = sample['query'].get('sql') or sample['query'].get('SQL') or sample['query'].get('query', '')
            schema_data = sample.get('table_schema') or sample.get('database_schema', {})
            gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
            schema = serializer.extract_schema_from_table_data(schema_data)
            
            print(f"\n   Sample {i}/{len(samples)}: {question[:60]}...")
            
            try:
                # Generate SQL without SafeSQL
                generated_sql = generator.generate(question, schema, guardrails=None)
                print(f"   Generated SQL: {generated_sql[:80]}...")
                
                # Get database connection for execution
                db_id = sample.get('db_id') or sample.get('table_id')
                db_conn = None
                if db_id and hasattr(loader, 'get_database_connection'):
                    db_conn = loader.get_database_connection(db_id)
                
                # Evaluate (simplified - just check if SQL is generated)
                print(f"   Status: SQL generated successfully")
                baseline_results.append({
                    "question": question,
                    "generated_sql": generated_sql,
                    "status": "success"
                })
                
                if db_conn:
                    db_conn.close()
                    
            except Exception as e:
                print(f"   Error: {e}")
                baseline_results.append({
                    "question": question,
                    "error": str(e),
                    "status": "failed"
                })
        
        # Test Model 1: GPT-4 + SafeSQL
        print(f"\n5. Testing Model 1: GPT-4 + SafeSQL (Guardrails + Verification)...")
        safesql_results = []
        
        for i, sample in enumerate(samples, 1):
            question = sample['query']['question']
            gold_sql_dict = sample['query'].get('sql') or sample['query'].get('SQL') or sample['query'].get('query', '')
            schema_data = sample.get('table_schema') or sample.get('database_schema', {})
            gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
            schema = serializer.extract_schema_from_table_data(schema_data)
            
            print(f"\n   Sample {i}/{len(samples)}: {question[:60]}...")
            
            try:
                # Generate SQL with SafeSQL
                generated_sql = generator.generate(question, schema, guardrails=guardrails)
                print(f"   Generated SQL: {generated_sql[:80]}...")
                
                # Verify SQL
                verification_result = verifier.verify(
                    generated_sql=generated_sql,
                    question=question,
                    schema=schema
                )
                
                if verification_result.get("is_valid"):
                    print(f"   Verification: PASSED")
                else:
                    print(f"   Verification: FAILED - {verification_result.get('errors', [])}")
                
                safesql_results.append({
                    "question": question,
                    "generated_sql": generated_sql,
                    "verification": verification_result,
                    "status": "success"
                })
                
            except Exception as e:
                print(f"   Error: {e}")
                safesql_results.append({
                    "question": question,
                    "error": str(e),
                    "status": "failed"
                })
        
        # Summary
        print(f"\n" + "=" * 70)
        print("Integration Test Summary")
        print("=" * 70)
        print(f"\nDataset: {dataset_name.upper()}")
        print(f"Samples tested: {len(samples)}")
        print(f"\nModel 3 (Baseline GPT-4):")
        print(f"  Successful: {sum(1 for r in baseline_results if r.get('status') == 'success')}")
        print(f"  Failed: {sum(1 for r in baseline_results if r.get('status') == 'failed')}")
        print(f"\nModel 1 (GPT-4 + SafeSQL):")
        print(f"  Successful: {sum(1 for r in safesql_results if r.get('status') == 'success')}")
        print(f"  Failed: {sum(1 for r in safesql_results if r.get('status') == 'failed')}")
        print(f"\nStatus: Integration test completed")
        
    except FileNotFoundError as e:
        print(f"\nError: Dataset not found - {e}")
        print(f"\nPlease ensure {dataset_name} dataset is downloaded to:")
        if dataset_name == "spider":
            print("  safesql/data/datasets/spider/")
            print("\nExpected structure:")
            print("  spider/")
            print("  ├── dev.json")
            print("  ├── train_spider.json")
            print("  ├── tables.json")
            print("  └── database/")
            print("      └── ...")
        elif dataset_name == "bird":
            print("  safesql/data/datasets/bird/")
            print("\nExpected structure:")
            print("  bird/")
            print("  ├── train/")
            print("  │   └── train.json")
            print("  ├── dev/")
            print("  │   └── dev.json")
            print("  └── dev_databases/")
            print("      └── ...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function."""
    print("=" * 70)
    print("BIRD Dataset Integration Test")
    print("Testing Models 1 and 3 with Spider and BIRD datasets")
    print("=" * 70)
    
    # Test Spider dataset
    print("\n")
    test_dataset_integration("spider", n_samples=2)
    
    # Test BIRD dataset
    print("\n\n")
    test_dataset_integration("bird", n_samples=2)
    
    print("\n" + "=" * 70)
    print("All integration tests completed")
    print("=" * 70)


if __name__ == "__main__":
    main()
