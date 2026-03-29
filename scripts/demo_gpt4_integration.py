"""Demo script showing SQL Generator integration with Verification Layer.

This demonstrates:
1. SQL Generator producing SQL from natural language
2. Verification Layer validating generated SQL
3. Complete end-to-end flow
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file BEFORE importing GPT4SQLGenerator
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        # Environment file loaded
except ImportError:
    pass

from src.models.gpt4_generator import GPT4SQLGenerator
from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification import Verifier
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def check_api_key():
    """Check if OpenAI API key is set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("=" * 70)
        print("ERROR: OpenAI API Key Not Found")
        print("=" * 70)
        print("\nTo use the SQL Generator, you need to set your OpenAI API key:")
        print("\nOption 1: Set environment variable")
        print("  Windows PowerShell:")
        print("    $env:OPENAI_API_KEY='your-api-key-here'")
        print("\n  Windows CMD:")
        print("    set OPENAI_API_KEY=your-api-key-here")
        print("\n  Linux/Mac:")
        print("    export OPENAI_API_KEY='your-api-key-here'")
        print("\nOption 2: Create .env file in safesql/ directory")
        print("  OPENAI_API_KEY=your-api-key-here")
        print("\nGet your API key from: https://platform.openai.com/api-keys")
        print("\n" + "=" * 70)
        return False
    return True


def main():
    """Demo SQL Generator integration."""
    print("=" * 70)
    print("SQL Generator Integration with Verification Layer - DEMO")
    print("=" * 70)
    
    # Check API key
    if not check_api_key():
        return
    
    print("\nStep 1: Initializing components...")
    try:
        generator = GPT4SQLGenerator()
        loader = WikiSQLValueLoader()
        serializer = WikiSQLValueSchemaSerializer()
        verifier = Verifier(enable_repair=True)
        print("   Status: All components initialized\n")
    except Exception as e:
        print(f"   Error: Failed to initialize: {e}")
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
    print("END-TO-END FLOW: SQL Generation -> Verification")
    print("=" * 70)
    
    for i, sample in enumerate(samples, 1):
        question = sample['query']['question']
        gold_sql = sample['query']['sql']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"Gold SQL: {loader.convert_sql_to_string(gold_sql, sample['table_schema'])}")
        
        # Step 1: Generate SQL
        print(f"\n[1] SQL Generation:")
        try:
            generated_sql_string = generator.generate(question, schema)
            print(f"    Generated SQL: {generated_sql_string}")
        except Exception as e:
            print(f"    Error: Generation failed: {e}")
            continue
        
        # Step 2: Verify generated SQL
        print(f"\n[2] Verification:")
        try:
            # For now, verify the SQL string directly
            # In production, you'd convert to structured format first
            result = verifier.verify(
                generated_sql_string,
                schema,
                question=question,
                gold_sql=gold_sql,
                max_repair_iterations=1
            )
            
            print(f"    Status: {result['status']}")
            print(f"    Safe to execute: {result['safe_to_execute']}")
            
            if result['repair_applied']:
                print(f"    Repair applied: Yes")
                for fix in result['fixes_applied']:
                    print(f"      - {fix}")
            
            if result['errors']:
                print(f"    Errors: {len(result['errors'])}")
                for error in result['errors'][:2]:
                    print(f"      - {error}")
            
            if result['warnings']:
                print(f"    Warnings: {len(result['warnings'])}")
                for warning in result['warnings'][:1]:
                    print(f"      - {warning}")
        
        except Exception as e:
            print(f"    Error: Verification failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("SQL GENERATION INTEGRATION COMPLETE")
    print("=" * 70)
    print("\nThis demonstrates:")
    print("1. SQL Generator produces SQL from natural language")
    print("2. Verification Layer validates the generated SQL")
    print("3. Auto-repair fixes errors if possible")
    print("4. Final safety decision is made")
    print("\nNext: Add Guardrails Layer to prevent unsafe operations during generation")


if __name__ == "__main__":
    main()
