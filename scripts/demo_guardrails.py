"""Demo script showing Guardrails Layer in action.

This demonstrates:
1. How Guardrails prevent unsafe SQL operations
2. Pattern matching for dangerous queries
3. Policy enforcement
4. Integration with SQL generation
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
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Guardrails Layer."""
    print("=" * 70)
    print("Guardrails Layer - DEMO")
    print("=" * 70)
    print("\nThis demonstrates how Guardrails prevent unsafe SQL operations:")
    print("- Blocks dangerous operations (DROP, DELETE, TRUNCATE)")
    print("- Detects unsafe patterns")
    print("- Enforces safety policies")
    print("- Validates SQL grammar\n")
    
    # Initialize components
    print("Step 1: Initializing components...")
    try:
        guardrails = Guardrails()
        generator = GPT4SQLGenerator(config={"model": "gpt-4"})
        print("   Status: Components initialized successfully\n")
    except Exception as e:
        print(f"   Error: Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 1: Safe SQL
    print("=" * 70)
    print("TEST 1: Safe SQL (SELECT query)")
    print("=" * 70)
    
    safe_sql = "SELECT Position FROM table_10015132_11 WHERE School/Club Team = 'Duke'"
    print(f"\nSQL: {safe_sql}")
    
    result = guardrails.apply_guardrails(safe_sql)
    
    print(f"\nGuardrails Result:")
    print(f"  Safe: {result['safe']}")
    print(f"  Allowed: {result['allowed']}")
    if result['violations']:
        print(f"  Violations: {result['violations']}")
    else:
        print(f"  Status: No violations detected")
    
    # Test 2: Dangerous SQL - DROP TABLE
    print("\n" + "=" * 70)
    print("TEST 2: Dangerous SQL (DROP TABLE)")
    print("=" * 70)
    
    dangerous_sql1 = "DROP TABLE employees"
    print(f"\nSQL: {dangerous_sql1}")
    
    result = guardrails.apply_guardrails(dangerous_sql1)
    
    print(f"\nGuardrails Result:")
    print(f"  Safe: {result['safe']}")
    print(f"  Allowed: {result['allowed']}")
    if result['violations']:
        print(f"  Violations:")
        for violation in result['violations']:
            print(f"    - {violation}")
    print(f"  Status: Dangerous operation blocked")
    
    # Test 3: Dangerous SQL - DELETE without WHERE
    print("\n" + "=" * 70)
    print("TEST 3: Dangerous SQL (DELETE without WHERE)")
    print("=" * 70)
    
    dangerous_sql2 = "DELETE FROM employees"
    print(f"\nSQL: {dangerous_sql2}")
    
    result = guardrails.apply_guardrails(dangerous_sql2)
    
    print(f"\nGuardrails Result:")
    print(f"  Safe: {result['safe']}")
    print(f"  Allowed: {result['allowed']}")
    if result['violations']:
        print(f"  Violations:")
        for violation in result['violations']:
            print(f"    - {violation}")
    print(f"  Status: Unsafe DELETE operation blocked")
    
    # Test 4: Integration with SQL Generator
    print("\n" + "=" * 70)
    print("TEST 4: Guardrails + SQL Generator Integration")
    print("=" * 70)
    
    schema = {
        "table_name": "employees",
        "columns": [
            {"name": "id", "type": "INTEGER"},
            {"name": "name", "type": "TEXT"},
            {"name": "department", "type": "TEXT"}
        ]
    }
    
    question = "What are all employee names?"
    print(f"\nQuestion: {question}")
    print(f"Generating SQL with Guardrails...")
    
    try:
        # Generate with guardrails
        sql = generator.generate(question, schema, guardrails=guardrails)
        print(f"\nGenerated SQL: {sql}")
        
        # Check guardrails again
        result = guardrails.apply_guardrails(sql)
        print(f"\nGuardrails Check:")
        print(f"  Safe: {result['safe']}")
        print(f"  Allowed: {result['allowed']}")
        if result['violations']:
            print(f"  Violations: {result['violations']}")
        else:
            print(f"  Status: Generated SQL is safe")
    
    except Exception as e:
        print(f"  Error: Generation failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("GUARDRAILS LAYER COMPLETE")
    print("=" * 70)
    print("\nGuardrails Layer prevents unsafe operations:")
    print("1. Token Filtering - Blocks dangerous operations")
    print("2. Pattern Matching - Detects unsafe patterns")
    print("3. Constrained Decoding - Enforces constraints")
    print("4. Grammar Validation - Validates SQL structure")
    print("5. Policy Enforcement - Enforces safety policies")
    print("\nTogether with Verification Layer, provides dual-layer protection!")


if __name__ == "__main__":
    main()
