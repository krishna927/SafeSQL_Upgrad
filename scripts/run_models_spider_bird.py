"""Run Model 1 (GPT-4 + SafeSQL) and Model 3 (Baseline GPT-4) on Spider and BIRD datasets.

This script:
1. Loads Spider and BIRD datasets
2. Runs Model 3 (Baseline GPT-4) on both datasets
3. Runs Model 1 (GPT-4 + SafeSQL) on both datasets
4. Saves results for analysis
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime

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
from src.models.llama_generator import LLaMASQLGenerator
from src.guardrails import Guardrails
from src.data.loaders.dataset_factory import create_loader
from src.data.preprocessors.schema_serializer_factory import create_serializer
from src.verification import Verifier
from src.evaluation import SafeSQLEvaluator
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def evaluate_model3_baseline(
    loader,
    serializer,
    evaluator,
    generator,
    samples: List[Dict],
    dataset_name: str,
    n_samples: int,
    model_name: str = "GPT-4"
) -> Dict:
    """
    Evaluate Model 3: Baseline GPT-4 (without SafeSQL).
    
    Args:
        loader: Dataset loader
        serializer: Schema serializer
        evaluator: SafeSQL evaluator
        generator: GPT-4 generator
        samples: List of sample queries
        dataset_name: Name of dataset
        n_samples: Number of samples to evaluate
        
    Returns:
        Dictionary with evaluation results
    """
    if "LLaMA" in model_name or "llama" in model_name.lower():
        model_label = "Model 2 Baseline (LLaMA-3)"
        display_label = "Model 2 Baseline: LLaMA-3"
    else:
        model_label = "Model 3 (Baseline GPT-4)"
        display_label = "Model 3: Baseline GPT-4"
    
    logger.info(f"\n{'='*70}")
    logger.info(f"{display_label} (without SafeSQL) - {dataset_name.upper()}")
    logger.info(f"{'='*70}")
    
    results = {
        "model": model_label,
        "dataset": dataset_name,
        "n_samples": min(n_samples, len(samples)),
        "queries": [],
        "metrics": {
            "execution_accuracy": 0.0,
            "exact_match": 0.0,
            "total": 0,
            "successful": 0,
            "failed": 0
        }
    }
    
    successful = 0
    total_ex = 0.0
    total_em = 0.0
    
    for i, sample in enumerate(samples[:n_samples], 1):
        try:
            question = sample['query']['question']
            # Handle different SQL field names and formats
            # Spider: 'query' field = SQL string, 'sql' field = parsed dict
            # WikiSQL_VALUE: 'sql_string' field = converted SQL string, 'query'['sql'] = structured dict
            if 'sql_string' in sample:
                # WikiSQL_VALUE format - already converted
                gold_sql = sample['sql_string'] or ''
            else:
                # Spider format - need to extract from 'query' field
                gold_sql_dict = sample['query'].get('query') or sample['query'].get('sql') or sample['query'].get('SQL', '')
                schema_data = sample.get('table_schema') or sample.get('database_schema', {})
                gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
            
            schema_data = sample.get('table_schema') or sample.get('database_schema', {})
            schema = serializer.extract_schema_from_table_data(schema_data)
            
            logger.info(f"\n[{i}/{min(n_samples, len(samples))}] {question[:60]}...")
            
            # Get database connection for execution (needed for column name fixes)
            db_id = sample.get('db_id') or sample.get('table_id')
            db_conn = None
            if hasattr(loader, 'get_database_connection'):
                try:
                    # Check dataset type to determine connection method
                    dataset_name = loader.get_dataset_name() if hasattr(loader, 'get_dataset_name') else ''
                    if dataset_name == 'wikisql_value':
                        # WikiSQL_VALUE uses split-based connection
                        split = sample.get('_split', 'dev')
                        db_conn = loader.get_database_connection(split)
                    elif db_id:
                        # Spider/BIRD use db_id-based connection
                        db_conn = loader.get_database_connection(db_id)
                    else:
                        # Fallback: try split-based
                        split = sample.get('_split', 'dev')
                        db_conn = loader.get_database_connection(split)
                except Exception as e:
                    logger.debug(f"Could not get database connection: {e}")
                    db_conn = None
            
            # Generate SQL without SafeSQL (baseline)
            # Pass db_connection for column name fixes
            generated_sql = generator.generate(question, schema, guardrails=None, db_connection=db_conn)
            
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
            
            ex = eval_result.get('ex', 0.0)
            em = eval_result.get('em', 0.0)
            
            total_ex += ex
            total_em += em
            successful += 1
            
            query_result = {
                "question": question,
                "generated_sql": generated_sql,
                "gold_sql": gold_sql,
                "execution_accuracy": ex,
                "exact_match": em,
                "status": "success"
            }
            results["queries"].append(query_result)
            
            logger.info(f"  EX: {ex:.2f}, EM: {em:.2f}")
            
            if db_conn:
                db_conn.close()
                
        except Exception as e:
            logger.error(f"  Error: {e}")
            results["metrics"]["failed"] += 1
            results["queries"].append({
                "question": sample.get('query', {}).get('question', 'Unknown'),
                "error": str(e),
                "status": "failed"
            })
    
    # Calculate metrics
    if successful > 0:
        results["metrics"]["execution_accuracy"] = total_ex / successful
        results["metrics"]["exact_match"] = total_em / successful
    results["metrics"]["total"] = len(samples[:n_samples])
    results["metrics"]["successful"] = successful
    
    logger.info(f"\nSummary:")
    logger.info(f"  Execution Accuracy: {results['metrics']['execution_accuracy']:.2%}")
    logger.info(f"  Exact Match: {results['metrics']['exact_match']:.2%}")
    logger.info(f"  Successful: {successful}/{len(samples[:n_samples])}")
    
    return results


def evaluate_model1_safesql(
    loader,
    serializer,
    evaluator,
    generator,
    guardrails,
    verifier,
    samples: List[Dict],
    dataset_name: str,
    n_samples: int,
    model_name: str = "GPT-4"
) -> Dict:
    """
    Evaluate Model 1: GPT-4 + SafeSQL (Guardrails + Verification).
    
    Args:
        loader: Dataset loader
        serializer: Schema serializer
        evaluator: SafeSQL evaluator
        generator: GPT-4 generator
        guardrails: Guardrails instance
        verifier: Verifier instance
        samples: List of sample queries
        dataset_name: Name of dataset
        n_samples: Number of samples to evaluate
        
    Returns:
        Dictionary with evaluation results
    """
    logger.info(f"\n{'='*70}")
    model_label = "Model 1: GPT-4" if not hasattr(evaluate_model1_safesql, '_model2') else "Model 2: LLaMA-3"
    logger.info(f"{model_label} + SafeSQL (Guardrails + Verification) - {dataset_name.upper()}")
    logger.info(f"{'='*70}")
    
    model_label = "Model 1 (GPT-4 + SafeSQL)" if not hasattr(evaluate_model1_safesql, '_model2') else "Model 2 (LLaMA-3 + SafeSQL)"
    results = {
        "model": model_label,
        "dataset": dataset_name,
        "n_samples": min(n_samples, len(samples)),
        "queries": [],
        "metrics": {
            "execution_accuracy": 0.0,
            "exact_match": 0.0,
            "safety_violations_prevented": 0,
            "auto_repair_success": 0,
            "total": 0,
            "successful": 0,
            "failed": 0
        }
    }
    
    successful = 0
    total_ex = 0.0
    total_em = 0.0
    safety_prevented = 0
    repair_success = 0
    
    for i, sample in enumerate(samples[:n_samples], 1):
        try:
            question = sample['query']['question']
            # Handle different SQL field names and formats
            # Spider: 'query' field = SQL string, 'sql' field = parsed dict
            # WikiSQL_VALUE: 'sql_string' field = converted SQL string, 'query'['sql'] = structured dict
            if 'sql_string' in sample:
                # WikiSQL_VALUE format - already converted
                gold_sql = sample['sql_string'] or ''
            else:
                # Spider format - need to extract from 'query' field
                gold_sql_dict = sample['query'].get('query') or sample['query'].get('sql') or sample['query'].get('SQL', '')
                schema_data = sample.get('table_schema') or sample.get('database_schema', {})
                gold_sql = loader.convert_sql_to_string(gold_sql_dict, schema_data)
            
            schema_data = sample.get('table_schema') or sample.get('database_schema', {})
            schema = serializer.extract_schema_from_table_data(schema_data)
            
            logger.info(f"\n[{i}/{min(n_samples, len(samples))}] {question[:60]}...")
            
            # Get database connection for execution (needed for column name fixes)
            db_id = sample.get('db_id') or sample.get('table_id')
            db_conn = None
            if hasattr(loader, 'get_database_connection'):
                try:
                    # Check dataset type to determine connection method
                    dataset_name = loader.get_dataset_name() if hasattr(loader, 'get_dataset_name') else ''
                    if dataset_name == 'wikisql_value':
                        # WikiSQL_VALUE uses split-based connection
                        split = sample.get('_split', 'dev')
                        db_conn = loader.get_database_connection(split)
                    elif db_id:
                        # Spider/BIRD use db_id-based connection
                        db_conn = loader.get_database_connection(db_id)
                    else:
                        # Fallback: try split-based
                        split = sample.get('_split', 'dev')
                        db_conn = loader.get_database_connection(split)
                except Exception as e:
                    logger.debug(f"Could not get database connection: {e}")
                    db_conn = None
            
            # Generate SQL with SafeSQL (guardrails)
            # Pass db_connection for column name fixes
            generated_sql = generator.generate(question, schema, guardrails=guardrails, db_connection=db_conn)
            
            # Verify SQL
            verification_result = verifier.verify(
                sql=generated_sql,
                schema=schema,
                question=question
            )
            
            # Check if repair was needed and successful
            if not verification_result.get("safe_to_execute"):
                if verification_result.get("repaired_sql"):
                    repair_success += 1
                    generated_sql = verification_result.get("repaired_sql")
                    logger.info(f"  Auto-repair applied")
                else:
                    safety_prevented += 1
                    errors = verification_result.get('errors', [])
                    logger.info(f"  Safety violation detected: {errors[:2] if errors else 'Unknown error'}")
            
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
            
            ex = eval_result.get('ex', 0.0)
            em = eval_result.get('em', 0.0)
            
            total_ex += ex
            total_em += em
            successful += 1
            
            query_result = {
                "question": question,
                "generated_sql": generated_sql,
                "gold_sql": gold_sql,
                "execution_accuracy": ex,
                "exact_match": em,
                "verification": verification_result,
                "status": "success"
            }
            results["queries"].append(query_result)
            
            logger.info(f"  EX: {ex:.2f}, EM: {em:.2f}")
            
            if db_conn:
                db_conn.close()
                
        except Exception as e:
            logger.error(f"  Error: {e}")
            results["metrics"]["failed"] += 1
            results["queries"].append({
                "question": sample.get('query', {}).get('question', 'Unknown'),
                "error": str(e),
                "status": "failed"
            })
    
    # Calculate metrics
    if successful > 0:
        results["metrics"]["execution_accuracy"] = total_ex / successful
        results["metrics"]["exact_match"] = total_em / successful
    results["metrics"]["total"] = len(samples[:n_samples])
    results["metrics"]["successful"] = successful
    results["metrics"]["safety_violations_prevented"] = safety_prevented
    results["metrics"]["auto_repair_success"] = repair_success
    
    logger.info(f"\nSummary:")
    logger.info(f"  Execution Accuracy: {results['metrics']['execution_accuracy']:.2%}")
    logger.info(f"  Exact Match: {results['metrics']['exact_match']:.2%}")
    logger.info(f"  Safety Violations Prevented: {safety_prevented}")
    logger.info(f"  Auto-Repair Success: {repair_success}")
    logger.info(f"  Successful: {successful}/{len(samples[:n_samples])}")
    
    return results


def main():
    """Main function to run evaluations."""
    parser = argparse.ArgumentParser(description="Run Model 1 and Model 3 on Spider and BIRD datasets")
    parser.add_argument("--n_samples", type=int, default=20, help="Number of samples per dataset (default: 20)")
    parser.add_argument("--spider_only", action="store_true", help="Run only on Spider dataset")
    parser.add_argument("--bird_only", action="store_true", help="Run only on BIRD dataset")
    parser.add_argument("--wikisql_only", action="store_true", help="Run only on WikiSQL_VALUE dataset")
    parser.add_argument("--dataset", type=str, default=None, choices=["wikisql", "spider", "bird"], help="Specific dataset to evaluate (overrides --*_only flags)")
    parser.add_argument("--model2", action="store_true", help="Use Model 2 (LLaMA-3, FREE) instead of GPT-4")
    parser.add_argument("--model2_provider", type=str, default="groq", choices=["groq", "huggingface"], help="Model 2 provider: 'groq' (free API) or 'huggingface' (local)")
    parser.add_argument("--output_dir", type=str, default="evaluation_results", help="Output directory for results")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=" * 70)
    
    # Initialize models
    logger.info("\nInitializing models...")
    if args.model2:
        logger.info("Using Model 2: LLaMA-3 (FREE)")
        logger.info(f"Provider: {args.model2_provider}")
        generator = LLaMASQLGenerator(config={
            "provider": args.model2_provider,
            "model": "llama-3.1-8b-instant" if args.model2_provider == "groq" else "meta-llama/Llama-3-8B-Instruct",
            "temperature": 0.0,
            "max_tokens": 512
        })
        model_name = "Model 2 (LLaMA-3)"
        logger.info(f"Running Model 2 ({model_name}) + SafeSQL on Datasets")
    else:
        logger.info("Using Model 1/3: GPT-4o (cheaper and better than legacy GPT-4)")
        generator = GPT4SQLGenerator(config={"model": "gpt-4o"})
        model_name = "GPT-4o"
        logger.info("Running Model 1 and Model 3 on Spider and BIRD Datasets")
    
    logger.info("=" * 70)
    logger.info(f"Number of samples per dataset: {args.n_samples}")
    logger.info(f"Output directory: {output_dir}")
    
    guardrails = Guardrails()
    verifier = Verifier(enable_repair=True)
    evaluator = SafeSQLEvaluator()
    logger.info("Models initialized successfully")
    
    all_results = {
        "timestamp": timestamp,
        "n_samples": args.n_samples,
        "results": {}
    }
    
    # Determine which datasets to evaluate
    evaluate_spider = args.dataset == "spider" or (args.dataset is None and not args.bird_only and not args.wikisql_only) or args.spider_only
    evaluate_bird = args.dataset == "bird" or (args.dataset is None and not args.spider_only and not args.wikisql_only) or args.bird_only
    evaluate_wikisql = args.dataset == "wikisql" or args.wikisql_only
    
    # Evaluate Spider dataset
    if evaluate_spider:
        try:
            logger.info("\n" + "=" * 70)
            logger.info("Loading Spider Dataset")
            logger.info("=" * 70)
            
            spider_loader = create_loader("spider")
            spider_serializer = create_serializer("spider")
            spider_samples = spider_loader.get_sample("dev", n=args.n_samples)
            
            logger.info(f"Loaded {len(spider_samples)} Spider samples")
            
            # Model 3: Baseline
            spider_model3 = evaluate_model3_baseline(
                spider_loader, spider_serializer, evaluator, generator,
                spider_samples, "spider", args.n_samples
            )
            all_results["results"]["spider_model3"] = spider_model3
            
            # Model 1: SafeSQL
            spider_model1 = evaluate_model1_safesql(
                spider_loader, spider_serializer, evaluator, generator,
                guardrails, verifier, spider_samples, "spider", args.n_samples
            )
            all_results["results"]["spider_model1"] = spider_model1
            
            # Save Spider results
            spider_output = output_dir / f"spider_results_{timestamp}.json"
            with open(spider_output, 'w', encoding='utf-8') as f:
                json.dump({
                    "spider_model3": spider_model3,
                    "spider_model1": spider_model1
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"\nSpider results saved to: {spider_output}")
            
        except Exception as e:
            logger.error(f"Error evaluating Spider dataset: {e}")
            import traceback
            traceback.print_exc()
    
    # Evaluate WikiSQL_VALUE dataset
    if evaluate_wikisql:
        try:
            logger.info("\n" + "=" * 70)
            logger.info("Loading WikiSQL_VALUE Dataset")
            logger.info("=" * 70)
            
            wikisql_loader = create_loader("wikisql")
            wikisql_serializer = create_serializer("wikisql")
            wikisql_samples = wikisql_loader.get_sample("dev", n=args.n_samples)
            
            logger.info(f"Loaded {len(wikisql_samples)} WikiSQL_VALUE samples")
            
            if args.model2:
                # Model 2: LLaMA-3 Baseline (no SafeSQL)
                wikisql_model2 = evaluate_model3_baseline(
                    wikisql_loader, wikisql_serializer, evaluator, generator,
                    wikisql_samples, "wikisql", args.n_samples
                )
                # Update model label for Model 2
                wikisql_model2["model"] = "Model 2 Baseline (LLaMA-3)"
                all_results["results"]["wikisql_model2"] = wikisql_model2
                
                # Save WikiSQL results
                wikisql_output = output_dir / f"wikisql_results_{timestamp}.json"
                with open(wikisql_output, 'w', encoding='utf-8') as f:
                    json.dump({
                        "wikisql_model2": wikisql_model2
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"\nWikiSQL_VALUE results saved to: {wikisql_output}")
            else:
                # Model 3: Baseline
                wikisql_model3 = evaluate_model3_baseline(
                    wikisql_loader, wikisql_serializer, evaluator, generator,
                    wikisql_samples, "wikisql", args.n_samples
                )
                all_results["results"]["wikisql_model3"] = wikisql_model3
                
                # Model 1: SafeSQL
                wikisql_model1 = evaluate_model1_safesql(
                    wikisql_loader, wikisql_serializer, evaluator, generator,
                    guardrails, verifier, wikisql_samples, "wikisql", args.n_samples
                )
                all_results["results"]["wikisql_model1"] = wikisql_model1
                
                # Save WikiSQL results
                wikisql_output = output_dir / f"wikisql_results_{timestamp}.json"
                with open(wikisql_output, 'w', encoding='utf-8') as f:
                    json.dump({
                        "wikisql_model3": wikisql_model3,
                        "wikisql_model1": wikisql_model1
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"\nWikiSQL_VALUE results saved to: {wikisql_output}")
            
        except Exception as e:
            logger.error(f"Error evaluating WikiSQL_VALUE dataset: {e}")
            import traceback
            traceback.print_exc()
    
    # Evaluate BIRD dataset
    if evaluate_bird:
        try:
            logger.info("\n" + "=" * 70)
            logger.info("Loading BIRD Dataset")
            logger.info("=" * 70)
            
            bird_loader = create_loader("bird")
            bird_serializer = create_serializer("bird")
            bird_samples = bird_loader.get_sample("dev", n=args.n_samples)
            
            logger.info(f"Loaded {len(bird_samples)} BIRD samples")
            
            # Model 3: Baseline
            bird_model3 = evaluate_model3_baseline(
                bird_loader, bird_serializer, evaluator, generator,
                bird_samples, "bird", args.n_samples
            )
            all_results["results"]["bird_model3"] = bird_model3
            
            # Model 1: SafeSQL
            bird_model1 = evaluate_model1_safesql(
                bird_loader, bird_serializer, evaluator, generator,
                guardrails, verifier, bird_samples, "bird", args.n_samples
            )
            all_results["results"]["bird_model1"] = bird_model1
            
            # Save BIRD results
            bird_output = output_dir / f"bird_results_{timestamp}.json"
            with open(bird_output, 'w', encoding='utf-8') as f:
                json.dump({
                    "bird_model3": bird_model3,
                    "bird_model1": bird_model1
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"\nBIRD results saved to: {bird_output}")
            
        except Exception as e:
            logger.error(f"Error evaluating BIRD dataset: {e}")
            import traceback
            traceback.print_exc()
    
    # Save combined results
    combined_output = output_dir / f"combined_results_{timestamp}.json"
    with open(combined_output, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "=" * 70)
    logger.info("Evaluation Complete")
    logger.info("=" * 70)
    logger.info(f"All results saved to: {output_dir}")
    logger.info(f"Combined results: {combined_output}")


if __name__ == "__main__":
    main()
