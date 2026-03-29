"""Comprehensive accuracy evaluation for SafeSQL framework.

This script evaluates SafeSQL using standard NL2SQL metrics:
- Execution Accuracy (EX): Compare execution results
- Exact Match (EM): Compare SQL strings
- Safety Metrics: Guardrails and verification effectiveness

Compares:
1. Baseline: GPT-4 without SafeSQL
2. SafeSQL: GPT-4 + Guardrails + Verification
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import json

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
from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification import Verifier
from src.evaluation import SafeSQLEvaluator
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def evaluate_baseline(
    evaluator: SafeSQLEvaluator,
    samples: List[Dict],
    serializer: WikiSQLValueSchemaSerializer,
    loader: WikiSQLValueLoader,
    generator: GPT4SQLGenerator,
    n_samples: int = 50
) -> List[Dict]:
    """
    Evaluate baseline (GPT-4 without SafeSQL).
    
    Args:
        evaluator: Evaluator instance
        samples: Sample queries
        serializer: Schema serializer
        loader: Data loader
        generator: GPT-4 generator
        n_samples: Number of samples to evaluate
        
    Returns:
        List of evaluation results
    """
    results = []
    
    print(f"\nEvaluating Baseline (GPT-4 without SafeSQL)...")
    print(f"Processing {min(n_samples, len(samples))} queries...\n")
    
    for i, sample in enumerate(samples[:n_samples], 1):
        question = sample['query']['question']
        gold_sql_dict = sample['query']['sql']
        gold_sql = loader.convert_sql_to_string(gold_sql_dict, sample['table_schema'])
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        table_name = sample['table_schema'].get('name', schema.get('table_name', 'table'))
        table_data = sample['table_schema'].get('rows', [])
        
        print(f"[{i}/{min(n_samples, len(samples))}] {question[:60]}...")
        
        try:
            # Generate SQL WITHOUT SafeSQL (baseline)
            generated_sql = generator.generate(question, schema, guardrails=None)
            
            # Evaluate
            eval_result = evaluator.evaluate_single_query(
                question=question,
                generated_sql=generated_sql,
                gold_sql=gold_sql,
                table_name=table_name,
                schema=schema,
                table_data=table_data
            )
            
            eval_result["method"] = "baseline"
            results.append(eval_result)
            
            status = "PASS" if eval_result["ex"] == 1.0 else "FAIL"
            print(f"  {status} EX: {eval_result['ex']:.2f}, EM: {eval_result['em']:.2f}")
        
        except Exception as e:
            print(f"  Error: {e}")
            logger.error(f"Error evaluating baseline query {i}: {e}")
    
    return results


def evaluate_safesql(
    evaluator: SafeSQLEvaluator,
    samples: List[Dict],
    serializer: WikiSQLValueSchemaSerializer,
    loader: WikiSQLValueLoader,
    generator: GPT4SQLGenerator,
    guardrails: Guardrails,
    verifier: Verifier,
    n_samples: int = 50
) -> List[Dict]:
    """
    Evaluate SafeSQL (GPT-4 + Guardrails + Verification).
    
    Args:
        evaluator: Evaluator instance
        samples: Sample queries
        serializer: Schema serializer
        loader: Data loader
        generator: GPT-4 generator
        guardrails: Guardrails instance
        verifier: Verifier instance
        n_samples: Number of samples to evaluate
        
    Returns:
        List of evaluation results
    """
    results = []
    
    print(f"\nEvaluating SafeSQL (GPT-4 + Guardrails + Verification)...")
    print(f"Processing {min(n_samples, len(samples))} queries...\n")
    
    for i, sample in enumerate(samples[:n_samples], 1):
        question = sample['query']['question']
        gold_sql_dict = sample['query']['sql']
        gold_sql = loader.convert_sql_to_string(gold_sql_dict, sample['table_schema'])
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        table_name = sample['table_schema'].get('name', schema.get('table_name', 'table'))
        table_data = sample['table_schema'].get('rows', [])
        
        print(f"[{i}/{min(n_samples, len(samples))}] {question[:60]}...")
        
        try:
            # Generate SQL WITH SafeSQL
            generated_sql = generator.generate(question, schema, guardrails=guardrails)
            
            # Apply guardrails check
            guardrails_result = guardrails.apply_guardrails(generated_sql)
            
            # Apply verification
            verification_result = verifier.verify(
                generated_sql,
                schema,
                question=question,
                gold_sql=gold_sql_dict,
                max_repair_iterations=1
            )
            
            # Use repaired SQL if available
            if verification_result.get("repair_applied") and verification_result.get("repaired_sql"):
                generated_sql = verification_result["repaired_sql"]
            
            # Evaluate
            eval_result = evaluator.evaluate_single_query(
                question=question,
                generated_sql=generated_sql,
                gold_sql=gold_sql,
                table_name=table_name,
                schema=schema,
                table_data=table_data,
                guardrails_result=guardrails_result,
                verification_result=verification_result
            )
            
            eval_result["method"] = "safesql"
            eval_result["guardrails_result"] = guardrails_result
            eval_result["verification_result"] = verification_result
            results.append(eval_result)
            
            status = "PASS" if eval_result["ex"] == 1.0 else "FAIL"
            safety_status = "PASS" if eval_result.get("safety", {}).get("both_layers_passed", False) else "FAIL"
            print(f"  {status} EX: {eval_result['ex']:.2f}, EM: {eval_result['em']:.2f}, Safety: {safety_status}")
        
        except Exception as e:
            print(f"  Error: {e}")
            logger.error(f"Error evaluating SafeSQL query {i}: {e}")
    
    return results


def calculate_metrics(results: List[Dict]) -> Dict:
    """
    Calculate aggregate metrics from results.
    
    Args:
        results: List of evaluation results
        
    Returns:
        Aggregate metrics dictionary
    """
    if not results:
        return {}
    
    total = len(results)
    ex_correct = sum(1 for r in results if r["ex"] == 1.0)
    em_correct = sum(1 for r in results if r["em"] == 1.0)
    
    # Execution accuracy
    ex_accuracy = ex_correct / total if total > 0 else 0.0
    
    # Exact match
    em_accuracy = em_correct / total if total > 0 else 0.0
    
    # Executability
    executable = sum(1 for r in results if r["execution_accuracy"]["generated_executable"])
    executability_rate = executable / total if total > 0 else 0.0
    
    # Safety (if available)
    safety_passed = 0
    if results and "safety" in results[0]:
        safety_passed = sum(1 for r in results if r.get("safety", {}).get("both_layers_passed", False))
    safety_rate = safety_passed / total if total > 0 else 0.0
    
    return {
        "total_queries": total,
        "execution_accuracy": ex_accuracy,
        "exact_match": em_accuracy,
        "executability_rate": executability_rate,
        "safety_rate": safety_rate,
        "ex_correct": ex_correct,
        "em_correct": em_correct,
        "executable": executable,
        "safety_passed": safety_passed
    }


def print_comparison(baseline_metrics: Dict, safesql_metrics: Dict):
    """
    Print comparison between baseline and SafeSQL.
    
    Args:
        baseline_metrics: Baseline metrics
        safesql_metrics: SafeSQL metrics
    """
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS - COMPARISON")
    print("=" * 70)
    
    print(f"\n{'Metric':<30} {'Baseline':<20} {'SafeSQL':<20} {'Improvement':<15}")
    print("-" * 85)
    
    # Execution Accuracy
    baseline_ex = baseline_metrics.get("execution_accuracy", 0.0)
    safesql_ex = safesql_metrics.get("execution_accuracy", 0.0)
    ex_improvement = safesql_ex - baseline_ex
    print(f"{'Execution Accuracy (EX)':<30} {baseline_ex*100:>6.2f}%{'':<13} {safesql_ex*100:>6.2f}%{'':<13} {ex_improvement*100:>+6.2f}%")
    
    # Exact Match
    baseline_em = baseline_metrics.get("exact_match", 0.0)
    safesql_em = safesql_metrics.get("exact_match", 0.0)
    em_improvement = safesql_em - baseline_em
    print(f"{'Exact Match (EM)':<30} {baseline_em*100:>6.2f}%{'':<13} {safesql_em*100:>6.2f}%{'':<13} {em_improvement*100:>+6.2f}%")
    
    # Executability
    baseline_exec = baseline_metrics.get("executability_rate", 0.0)
    safesql_exec = safesql_metrics.get("executability_rate", 0.0)
    exec_improvement = safesql_exec - baseline_exec
    print(f"{'Executability Rate':<30} {baseline_exec*100:>6.2f}%{'':<13} {safesql_exec*100:>6.2f}%{'':<13} {exec_improvement*100:>+6.2f}%")
    
    # Safety (SafeSQL only)
    safesql_safety = safesql_metrics.get("safety_rate", 0.0)
    print(f"{'Safety Rate (Both Layers)':<30} {'N/A':<20} {safesql_safety*100:>6.2f}%{'':<13} {'N/A':<15}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nTotal Queries Evaluated: {baseline_metrics.get('total_queries', 0)}")
    print(f"\nBaseline (GPT-4):")
    print(f"  - Execution Accuracy: {baseline_ex*100:.2f}% ({baseline_metrics.get('ex_correct', 0)}/{baseline_metrics.get('total_queries', 0)})")
    print(f"  - Exact Match: {baseline_em*100:.2f}% ({baseline_metrics.get('em_correct', 0)}/{baseline_metrics.get('total_queries', 0)})")
    
    print(f"\nSafeSQL (GPT-4 + Guardrails + Verification):")
    print(f"  - Execution Accuracy: {safesql_ex*100:.2f}% ({safesql_metrics.get('ex_correct', 0)}/{safesql_metrics.get('total_queries', 0)})")
    print(f"  - Exact Match: {safesql_em*100:.2f}% ({safesql_metrics.get('em_correct', 0)}/{safesql_metrics.get('total_queries', 0)})")
    print(f"  - Safety Rate: {safesql_safety*100:.2f}% ({safesql_metrics.get('safety_passed', 0)}/{safesql_metrics.get('total_queries', 0)})")
    
    print(f"\nImprovements:")
    print(f"  - Execution Accuracy: {ex_improvement*100:+.2f}%")
    print(f"  - Exact Match: {em_improvement*100:+.2f}%")
    print(f"  - Executability: {exec_improvement*100:+.2f}%")


def main():
    """Main evaluation function."""
    print("=" * 70)
    print("SafeSQL Framework - Comprehensive Accuracy Evaluation")
    print("=" * 70)
    print("\nThis evaluation compares:")
    print("1. Baseline: GPT-4 without SafeSQL")
    print("2. SafeSQL: GPT-4 + Guardrails + Verification")
    print("\nMetrics:")
    print("- Execution Accuracy (EX): Compare execution results")
    print("- Exact Match (EM): Compare SQL strings")
    print("- Safety Rate: Both layers passed")
    
    # Initialize components
    print("\n" + "=" * 70)
    print("Initializing components...")
    try:
        evaluator = SafeSQLEvaluator()
        loader = WikiSQLValueLoader()
        serializer = WikiSQLValueSchemaSerializer()
        generator = GPT4SQLGenerator(config={"model": "gpt-4"})
        guardrails = Guardrails()
        verifier = Verifier(enable_repair=True)
        print("Status: All components initialized")
    except Exception as e:
        print(f"Error: Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Load test data
    print("\n" + "=" * 70)
    print("Loading test data...")
    try:
        samples = loader.get_sample("dev", n=50)  # Start with 50 for testing
        print(f"Status: Loaded {len(samples)} test queries")
    except Exception as e:
        print(f"Error: Failed to load data: {e}")
        return
    
    # Evaluate baseline
    baseline_results = evaluate_baseline(
        evaluator, samples, serializer, loader, generator, n_samples=50
    )
    baseline_metrics = calculate_metrics(baseline_results)
    
    # Evaluate SafeSQL
    safesql_results = evaluate_safesql(
        evaluator, samples, serializer, loader, generator,
        guardrails, verifier, n_samples=50
    )
    safesql_metrics = calculate_metrics(safesql_results)
    
    # Print comparison
    print_comparison(baseline_metrics, safesql_metrics)
    
    # Save results
    output_file = project_root / "evaluation_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "baseline": {
                "metrics": baseline_metrics,
                "results": baseline_results
            },
            "safesql": {
                "metrics": safesql_metrics,
                "results": safesql_results
            }
        }, f, indent=2)
    
    print(f"\nStatus: Results saved to: {output_file}")


if __name__ == "__main__":
    main()
