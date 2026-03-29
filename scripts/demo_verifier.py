"""Demo script to show Verification Orchestrator in action.

This demonstrates:
1. How Verifier coordinates all validation components
2. Complete verification pipeline
3. Auto-repair integration
4. Final safety decision
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification.verifier import Verifier
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Verifier."""
    print("=" * 70)
    print("Verification Orchestrator - DEMO")
    print("=" * 70)
    print("\nThis demonstrates the complete verification pipeline:\n")
    print("1. Schema Validator - Checks tables/columns/types")
    print("2. Constraint Checker - Checks operators/aggregations/logic")
    print("3. Semantic Analyzer - Checks SQL matches question intent")
    print("4. Auto-Repair - Fixes common errors automatically")
    print("5. Verifier - Coordinates all components\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing verifier...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    verifier = Verifier(enable_repair=True)
    print("   Status: Verifier initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries...")
    samples = loader.get_sample("dev", n=5)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    safe_count = 0
    repaired_count = 0
    unsafe_count = 0
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        
        # Verify gold standard SQL (should be safe)
        result = verifier.verify(gold_sql, schema, question, gold_sql)
        
        print(f"\nVerification Result:")
        print(f"  Status: {result['status']}")
        print(f"  Safe to execute: {result['safe_to_execute']}")
        
        if result['repair_applied']:
            repaired_count += 1
            print(f"  Repair applied: Yes")
            for fix in result['fixes_applied']:
                print(f"    - {fix}")
        
        if result['errors']:
            unsafe_count += 1
            print(f"  Errors: {len(result['errors'])}")
        else:
            safe_count += 1
        
        if result['warnings']:
            print(f"  Warnings: {len(result['warnings'])}")
    
    # Test with broken SQL
    print("\n" + "=" * 70)
    print("TESTING WITH BROKEN SQL")
    print("=" * 70)
    
    if samples:
        sample = samples[0]
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        # Create broken SQL
        broken_sql = gold_sql.copy()
        broken_sql['agg'] = 4  # SUM (wrong type)
        
        print(f"\nQuestion: {question}")
        print(f"Broken SQL: Changed aggregation to SUM")
        
        result = verifier.verify(broken_sql, schema, question, gold_sql, max_repair_iterations=2)
        
        print(f"\nVerification Result:")
        print(f"  Status: {result['status']}")
        print(f"  Safe to execute: {result['safe_to_execute']}")
        
        if result['repair_applied']:
            print(f"  Repair applied: Yes")
            for fix in result['fixes_applied']:
                print(f"    - {fix}")
            print(f"\n  Repaired SQL: agg={result['repaired_sql'].get('agg')}")
        
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")
            for error in result['errors'][:2]:
                print(f"    - {error}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Safe queries: {safe_count}")
    print(f"Repaired queries: {repaired_count}")
    print(f"Unsafe queries: {unsafe_count}")
    print(f"Total tested: {len(samples)}")
    
    print("\n" + "=" * 70)
    print("VERIFICATION PIPELINE COMPLETE")
    print("=" * 70)
    print("\nThe Verifier coordinates all validation components to ensure SQL safety.")
    print("It provides a unified interface for SQL verification and repair.")


if __name__ == "__main__":
    main()
