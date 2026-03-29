"""Complete SafeSQL System Demo - Guardrails + SQL Generator + Verification.

This demonstrates the complete dual-layer SafeSQL system:
1. Guardrails Layer (Layer 1) - Prevents unsafe operations
2. SQL Generation - Generates SQL from natural language
3. Verification Layer (Layer 2) - Validates SQL
"""

import os
import sys
from pathlib import Path

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
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo complete SafeSQL system."""
    print("=" * 70)
    print("Complete SafeSQL System - Dual-Layer Protection")
    print("=" * 70)
    print("\nThis demonstrates the complete system:")
    print("1. Guardrails Layer (Layer 1) - Prevents unsafe operations")
    print("2. SQL Generation - Generates SQL from natural language")
    print("3. Verification Layer (Layer 2) - Validates SQL safety")
    print("4. Final Decision - Safe to Execute or Reject\n")
    
    # Initialize components
    print("Step 1: Initializing all components...")
    try:
        guardrails = Guardrails()
        generator = GPT4SQLGenerator(config={"model": "gpt-4"})
        loader = WikiSQLValueLoader()
        serializer = WikiSQLValueSchemaSerializer()
        verifier = Verifier(enable_repair=True)
        print("   Status: All components initialized\n")
    except Exception as e:
        print(f"   Error: Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get sample data
    print("Step 2: Loading sample queries...")
    try:
        samples = loader.get_sample("dev", n=3)
        print(f"   Status: Loaded {len(samples)} sample queries\n")
    except Exception as e:
        print(f"   Error: Failed to load data: {e}")
        return
    
    print("=" * 70)
    print("COMPLETE SYSTEM FLOW")
    print("=" * 70)
    
    for i, sample in enumerate(samples, 1):
        question = sample['query']['question']
        gold_sql = sample['query']['sql']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"Gold SQL: {loader.convert_sql_to_string(gold_sql, sample['table_schema'])}")
        
        # Step 1: Generate SQL with Generator + Guardrails
        print(f"\n[1] SQL Generation (with Guardrails):")
        try:
            generated_sql = generator.generate(question, schema, guardrails=guardrails)
            print(f"    Generated SQL: {generated_sql}")
        except Exception as e:
            print(f"    Error: Generation failed: {e}")
            continue
        
        # Step 2: Guardrails Check (Layer 1)
        print(f"\n[2] Guardrails Layer (Layer 1) - Prevention:")
        guardrails_result = guardrails.apply_guardrails(generated_sql)
        if guardrails_result['safe']:
            print(f"    Status: Guardrails check passed")
        else:
            print(f"    Status: Guardrails detected violations")
            for violation in guardrails_result['violations'][:3]:
                print(f"      - {violation}")
            print(f"    Result: Blocked by Guardrails Layer")
            continue
        
        # Step 3: Verification Layer (Layer 2)
        print(f"\n[3] Verification Layer (Layer 2) - Validation:")
        verification_result = verifier.verify(
            generated_sql,
            schema,
            question=question,
            gold_sql=gold_sql,
            max_repair_iterations=1
        )
        
        print(f"    Status: {verification_result['status']}")
        print(f"    Safe to execute: {verification_result['safe_to_execute']}")
        
        if verification_result['repair_applied']:
            print(f"    Repair applied: Yes")
            for fix in verification_result['fixes_applied']:
                print(f"      - {fix}")
        
        if verification_result['errors']:
            print(f"    Errors: {len(verification_result['errors'])}")
            for error in verification_result['errors'][:2]:
                print(f"      - {error}")
        
        # Step 4: Final Decision
        print(f"\n[4] Final Decision:")
        if guardrails_result['safe'] and verification_result['safe_to_execute']:
            print(f"    Status: SAFE TO EXECUTE")
            print(f"    Result: Both layers passed - SQL is safe")
        elif not guardrails_result['safe']:
            print(f"    Status: Blocked by Guardrails Layer")
        elif not verification_result['safe_to_execute']:
            print(f"    Status: Rejected by Verification Layer")
        else:
            print(f"    Status: SQL rejected")
    
    # Test with intentionally unsafe query
    print("\n" + "=" * 70)
    print("TESTING UNSAFE QUERY DETECTION")
    print("=" * 70)
    
    unsafe_queries = [
        "DROP TABLE employees",
        "DELETE FROM employees",
        "TRUNCATE TABLE employees"
    ]
    
    for unsafe_sql in unsafe_queries:
        print(f"\nUnsafe SQL: {unsafe_sql}")
        result = guardrails.apply_guardrails(unsafe_sql)
        if not result['safe']:
            print(f"  Status: Guardrails detected violation")
            print(f"  Details: {result['violations'][0]}")
        else:
            print(f"  Status: Not blocked")
    
    print("\n" + "=" * 70)
    print("COMPLETE SYSTEM SUMMARY")
    print("=" * 70)
    print("\nDual-Layer Protection:")
    print("1. Guardrails Layer (Layer 1) - Prevents unsafe operations")
    print("2. Verification Layer (Layer 2) - Validates SQL safety")
    print("\nTogether, they provide comprehensive SQL safety!")


if __name__ == "__main__":
    main()
