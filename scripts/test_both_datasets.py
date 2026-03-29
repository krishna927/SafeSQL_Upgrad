"""Test both Spider and WikiSQL_VALUE datasets with sample evaluations.

This script tests Model 1 and Model 3 on both datasets to ensure everything works
before running full evaluations.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict

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


def test_dataset(dataset_name: str, n_samples: int = 3):
    """Test a dataset with both models."""
    print("\n" + "=" * 70)
    print(f"Testing {dataset_name.upper()} Dataset")
    print("=" * 70)
    
    try:
        # Initialize loader and serializer
        loader = create_loader(dataset_name)
        serializer = create_serializer(dataset_name)
        print(f"[OK] Loader and serializer created")
        
        # Load samples
        samples = loader.get_sample("dev", n=n_samples)
        print(f"[OK] Loaded {len(samples)} samples")
        
        if not samples:
            print(f"[ERROR] No samples loaded")
            return False
        
        # Initialize models
        generator = GPT4SQLGenerator(config={"model": "gpt-4"})
        guardrails = Guardrails()
        verifier = Verifier(enable_repair=True)
        evaluator = SafeSQLEvaluator()
        print(f"[OK] Models initialized")
        
        # Test Model 3: Baseline
        print(f"\n--- Testing Model 3 (Baseline GPT-4) ---")
        model3_success = 0
        for i, sample in enumerate(samples, 1):
            try:
                question = sample['query']['question']
                # Handle different SQL field names
                gold_sql_dict = sample['query'].get('query') or sample['query'].get('sql') or sample['query'].get('SQL', '')
                schema_data = sample.get('table_schema') or sample.get('database_schema', {})
                gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
                schema = serializer.extract_schema_from_table_data(schema_data)
                
                # Generate SQL
                generated_sql = generator.generate(question, schema, guardrails=None)
                
                # Get database connection
                db_id = sample.get('db_id') or sample.get('table_id')
                db_conn = None
                if db_id and hasattr(loader, 'get_database_connection'):
                    try:
                        db_conn = loader.get_database_connection(db_id)
                    except:
                        # Try split-based connection for WikiSQL
                        if hasattr(loader, 'get_database_connection'):
                            try:
                                db_conn = loader.get_database_connection("dev")
                            except:
                                pass
                
                # Evaluate
                eval_result = evaluator.evaluate_single_query(
                    question=question,
                    generated_sql=generated_sql,
                    gold_sql=gold_sql,
                    table_name=schema.get('table_name') or schema.get('database_name', 'table'),
                    schema=schema,
                    table_data=schema_data.get('rows', []),
                    db_connection=db_conn
                )
                
                model3_success += 1
                print(f"  Sample {i}: [OK] EX={eval_result.get('ex', 0):.2f}, EM={eval_result.get('em', 0):.2f}")
                
                if db_conn:
                    db_conn.close()
                    
            except Exception as e:
                print(f"  Sample {i}: [ERROR] {str(e)[:80]}")
        
        # Test Model 1: SafeSQL
        print(f"\n--- Testing Model 1 (GPT-4 + SafeSQL) ---")
        model1_success = 0
        for i, sample in enumerate(samples, 1):
            try:
                question = sample['query']['question']
                gold_sql_dict = sample['query'].get('query') or sample['query'].get('sql') or sample['query'].get('SQL', '')
                schema_data = sample.get('table_schema') or sample.get('database_schema', {})
                gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
                schema = serializer.extract_schema_from_table_data(schema_data)
                
                # Generate SQL with SafeSQL
                generated_sql = generator.generate(question, schema, guardrails=guardrails)
                
                # Verify SQL
                verification_result = verifier.verify(
                    sql=generated_sql,
                    schema=schema,
                    question=question
                )
                
                # Get database connection
                db_id = sample.get('db_id') or sample.get('table_id')
                db_conn = None
                if db_id and hasattr(loader, 'get_database_connection'):
                    try:
                        db_conn = loader.get_database_connection(db_id)
                    except:
                        try:
                            db_conn = loader.get_database_connection("dev")
                        except:
                            pass
                
                # Evaluate
                eval_result = evaluator.evaluate_single_query(
                    question=question,
                    generated_sql=generated_sql,
                    gold_sql=gold_sql,
                    table_name=schema.get('table_name') or schema.get('database_name', 'table'),
                    schema=schema,
                    table_data=schema_data.get('rows', []),
                    db_connection=db_conn
                )
                
                model1_success += 1
                repair = " [REPAIR]" if verification_result.get('repair_applied') else ""
                print(f"  Sample {i}: [OK] EX={eval_result.get('ex', 0):.2f}, EM={eval_result.get('em', 0):.2f}{repair}")
                
                if db_conn:
                    db_conn.close()
                    
            except Exception as e:
                print(f"  Sample {i}: [ERROR] {str(e)[:80]}")
        
        # Summary
        print(f"\n--- Summary for {dataset_name.upper()} ---")
        print(f"  Model 3 Success: {model3_success}/{len(samples)}")
        print(f"  Model 1 Success: {model1_success}/{len(samples)}")
        
        return model3_success == len(samples) and model1_success == len(samples)
        
    except Exception as e:
        print(f"[ERROR] Failed to test {dataset_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("=" * 70)
    print("Testing Spider and WikiSQL_VALUE Datasets")
    print("=" * 70)
    print("\nThis will test both Model 1 and Model 3 on sample queries")
    print("to ensure everything works before full evaluation.\n")
    
    results = {}
    
    # Test Spider
    results['spider'] = test_dataset('spider', n_samples=3)
    
    # Test WikiSQL_VALUE
    results['wikisql'] = test_dataset('wikisql', n_samples=3)
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"\nSpider Dataset: {'[OK] Ready' if results.get('spider') else '[ERROR] Issues Found'}")
    print(f"WikiSQL_VALUE Dataset: {'[OK] Ready' if results.get('wikisql') else '[ERROR] Issues Found'}")
    
    if all(results.values()):
        print("\n[SUCCESS] Both datasets are ready for full evaluation!")
        print("\nYou can now run:")
        print("  python scripts/run_models_spider_bird.py --spider_only --n_samples 50")
        print("  python scripts/run_models_spider_bird.py --dataset wikisql --n_samples 50")
    else:
        print("\n[WARNING] Some issues found. Please review errors above.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
