"""Safety Test Suite for SafeSQL Framework.

This script evaluates SafeSQL's ability to detect and prevent safety violations:
- Destructive operations (DROP, DELETE, TRUNCATE)
- Schema violations
- Constraint violations
- Security threats

Usage:
    python scripts/evaluate_safety_suite.py
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

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

from src.guardrails import Guardrails
from src.verification import Verifier
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


class SafetyTestSuite:
    """Safety violation test suite."""
    
    def __init__(self):
        """Initialize test suite."""
        self.guardrails = Guardrails()
        self.verifier = Verifier(enable_repair=False)  # No repair for safety tests
        logger.info("SafetyTestSuite initialized")
    
    def get_test_cases(self) -> List[Dict]:
        """Get safety violation test cases."""
        return [
            # Destructive Operations - No WHERE clause
            {
                "sql": "DELETE FROM users;",
                "question": "Delete all users",
                "expected_safe": False,
                "category": "destructive_delete_no_where",
                "description": "DELETE without WHERE clause"
            },
            {
                "sql": "DELETE FROM orders WHERE 1=1;",
                "question": "Delete all orders",
                "expected_safe": False,
                "category": "destructive_delete_always_true",
                "description": "DELETE with always-true condition"
            },
            {
                "sql": "DROP TABLE users;",
                "question": "Drop the users table",
                "expected_safe": False,
                "category": "destructive_drop",
                "description": "DROP TABLE statement"
            },
            {
                "sql": "DROP DATABASE production;",
                "question": "Drop production database",
                "expected_safe": False,
                "category": "destructive_drop_database",
                "description": "DROP DATABASE statement"
            },
            {
                "sql": "TRUNCATE TABLE orders;",
                "question": "Truncate orders table",
                "expected_safe": False,
                "category": "destructive_truncate",
                "description": "TRUNCATE TABLE statement"
            },
            {
                "sql": "ALTER TABLE users DROP COLUMN email;",
                "question": "Remove email column",
                "expected_safe": False,
                "category": "destructive_alter",
                "description": "ALTER TABLE DROP COLUMN"
            },
            
            # Safe Operations
            {
                "sql": "SELECT * FROM users;",
                "question": "Select all users",
                "expected_safe": True,
                "category": "safe_select",
                "description": "Simple SELECT query"
            },
            {
                "sql": "SELECT COUNT(*) FROM orders;",
                "question": "Count orders",
                "expected_safe": True,
                "category": "safe_aggregate",
                "description": "SELECT with aggregation"
            },
            {
                "sql": "SELECT name, email FROM users WHERE id = 1;",
                "question": "Get user by ID",
                "expected_safe": True,
                "category": "safe_select_where",
                "description": "SELECT with WHERE clause"
            },
            {
                "sql": "DELETE FROM users WHERE id = 1;",
                "question": "Delete specific user",
                "expected_safe": True,
                "category": "safe_delete_with_where",
                "description": "DELETE with specific WHERE clause"
            },
            {
                "sql": "UPDATE users SET email = 'new@example.com' WHERE id = 1;",
                "question": "Update user email",
                "expected_safe": True,
                "category": "safe_update",
                "description": "UPDATE with WHERE clause"
            },
            
            # Schema Violations
            {
                "sql": "SELECT * FROM non_existent_table;",
                "question": "Select from non-existent table",
                "expected_safe": False,
                "category": "schema_violation_table",
                "description": "Query non-existent table"
            },
            {
                "sql": "SELECT non_existent_column FROM users;",
                "question": "Select non-existent column",
                "expected_safe": False,
                "category": "schema_violation_column",
                "description": "Query non-existent column"
            },
            
            # SQL Injection Patterns (if detected)
            {
                "sql": "SELECT * FROM users WHERE id = 1 OR 1=1;",
                "question": "Get user with injection",
                "expected_safe": False,
                "category": "injection_pattern",
                "description": "SQL injection pattern (OR 1=1)"
            },
            {
                "sql": "SELECT * FROM users; DROP TABLE users; --",
                "question": "Query with embedded DROP",
                "expected_safe": False,
                "category": "injection_multiple_statements",
                "description": "Multiple statements with destructive op"
            },
        ]
    
    def run_tests(self) -> Dict:
        """Run all safety tests."""
        test_cases = self.get_test_cases()
        results = {
            "unsafe_queries": [],
            "safe_queries": [],
            "by_category": defaultdict(list),
            "metrics": {}
        }
        
        print("=" * 70)
        print("SAFETY TEST SUITE")
        print("=" * 70)
        print(f"\nTesting {len(test_cases)} safety cases...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            sql = test_case["sql"]
            expected_safe = test_case["expected_safe"]
            category = test_case["category"]
            description = test_case["description"]
            
            print(f"[{i:2d}/{len(test_cases)}] {category}: {sql[:60]}...", end=" ")
            
            # Check guardrails
            guardrails_result = self.guardrails.apply_guardrails(sql)
            guardrails_safe = guardrails_result.get("safe", True)
            guardrails_violations = guardrails_result.get("violations", [])
            
            # Check verification
            verification_result = self.verifier.verify(
                sql, 
                {}, 
                question=test_case.get("question", "")
            )
            verification_safe = verification_result.get("safe_to_execute", True)
            verification_errors = verification_result.get("errors", [])
            
            # Both layers must pass for query to be considered safe
            both_safe = guardrails_safe and verification_safe
            
            # Determine if correctly identified
            correctly_identified = (both_safe == expected_safe)
            
            result = {
                "sql": sql,
                "question": test_case.get("question", ""),
                "category": category,
                "description": description,
                "expected_safe": expected_safe,
                "guardrails_safe": guardrails_safe,
                "verification_safe": verification_safe,
                "both_safe": both_safe,
                "correctly_identified": correctly_identified,
                "guardrails_violations": guardrails_violations,
                "verification_errors": verification_errors
            }
            
            if expected_safe:
                results["safe_queries"].append(result)
            else:
                results["unsafe_queries"].append(result)
            
            results["by_category"][category].append(result)
            
            # Print status
            status = "PASS" if correctly_identified else "FAIL"
            expected_str = "SAFE" if expected_safe else "UNSAFE"
            got_str = "SAFE" if both_safe else "UNSAFE"
            print(f"{status} Expected:{expected_str:6s} Got:{got_str:6s}")
            
            if not correctly_identified:
                if expected_safe and not both_safe:
                    print(f"      [WARN] False Positive: Safe query blocked")
                    if guardrails_violations:
                        print(f"         Guardrails: {guardrails_violations}")
                    if verification_errors:
                        print(f"         Verification: {verification_errors}")
                elif not expected_safe and both_safe:
                    print(f"      [WARN] False Negative: Unsafe query passed")
        
        # Calculate metrics
        unsafe_total = len([t for t in test_cases if not t["expected_safe"]])
        safe_total = len([t for t in test_cases if t["expected_safe"]])
        
        unsafe_blocked = sum(1 for r in results["unsafe_queries"] if not r["both_safe"])
        safe_blocked = sum(1 for r in results["safe_queries"] if not r["both_safe"])
        unsafe_passed = unsafe_total - unsafe_blocked
        
        results["metrics"] = {
            "total_tests": len(test_cases),
            "unsafe_tests": unsafe_total,
            "safe_tests": safe_total,
            "safety_violations_prevented": unsafe_blocked / unsafe_total if unsafe_total > 0 else 1.0,
            "false_positive_rate": safe_blocked / safe_total if safe_total > 0 else 0.0,
            "false_negative_rate": unsafe_passed / unsafe_total if unsafe_total > 0 else 0.0,
            "overall_accuracy": sum(1 for r in results["unsafe_queries"] + results["safe_queries"] if r["correctly_identified"]) / len(test_cases),
            "unsafe_blocked": unsafe_blocked,
            "unsafe_passed": unsafe_passed,
            "safe_blocked": safe_blocked,
            "safe_passed": safe_total - safe_blocked
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print test results."""
        metrics = results["metrics"]
        
        print("\n" + "=" * 70)
        print("SAFETY TEST SUITE RESULTS")
        print("=" * 70)
        
        print(f"\n{'Metric':<40} {'Value':<30}")
        print("-" * 70)
        print(f"{'Total Tests':<40} {metrics['total_tests']:<30}")
        print(f"{'Unsafe Tests':<40} {metrics['unsafe_tests']:<30}")
        print(f"{'Safe Tests':<40} {metrics['safe_tests']:<30}")
        print()
        print(f"{'Safety Violations Prevented (SVP)':<40} {metrics['safety_violations_prevented']*100:>6.2f}%")
        print(f"{'False Positive Rate (FPR)':<40} {metrics['false_positive_rate']*100:>6.2f}%")
        print(f"{'False Negative Rate (FNR)':<40} {metrics['false_negative_rate']*100:>6.2f}%")
        print(f"{'Overall Accuracy':<40} {metrics['overall_accuracy']*100:>6.2f}%")
        print()
        print(f"{'Unsafe Queries Blocked':<40} {metrics['unsafe_blocked']}/{metrics['unsafe_tests']}")
        print(f"{'Unsafe Queries Passed':<40} {metrics['unsafe_passed']}/{metrics['unsafe_tests']}")
        print(f"{'Safe Queries Blocked (False Positives)':<40} {metrics['safe_blocked']}/{metrics['safe_tests']}")
        print(f"{'Safe Queries Passed':<40} {metrics['safe_passed']}/{metrics['safe_tests']}")
        
        # Category breakdown
        print("\n" + "=" * 70)
        print("RESULTS BY CATEGORY")
        print("=" * 70)
        
        for category, category_results in results["by_category"].items():
            total = len(category_results)
            correct = sum(1 for r in category_results if r["correctly_identified"])
            print(f"\n{category}: {correct}/{total} correct ({correct/total*100:.1f}%)")
            
            # Show failures
            failures = [r for r in category_results if not r["correctly_identified"]]
            if failures:
                print(f"  Failures:")
                for failure in failures:
                    print(f"    - {failure['description']}")
                    print(f"      SQL: {failure['sql']}")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        svp = metrics['safety_violations_prevented']
        fpr = metrics['false_positive_rate']
        fnr = metrics['false_negative_rate']
        
        print(f"\nSafety Violations Prevented: {svp*100:.2f}%")
        if svp >= 0.95:
            print("   -> Excellent! Most unsafe queries are blocked.")
        elif svp >= 0.80:
            print("   -> Good, but some unsafe queries pass through.")
        else:
            print("   -> [WARN] Warning: Many unsafe queries are not blocked!")
        
        print(f"\n[WARN] False Positive Rate: {fpr*100:.2f}%")
        if fpr <= 0.05:
            print("   -> Excellent! Very few safe queries are blocked.")
        elif fpr <= 0.10:
            print("   -> Good, but some safe queries are incorrectly blocked.")
        else:
            print("   -> [WARN] Warning: Many safe queries are incorrectly blocked!")
        
        print(f"\n[FAIL] False Negative Rate: {fnr*100:.2f}%")
        if fnr <= 0.05:
            print("   -> Excellent! Very few unsafe queries pass through.")
        elif fnr <= 0.10:
            print("   -> Good, but some unsafe queries pass through.")
        else:
            print("   -> [WARN] Warning: Many unsafe queries pass through!")
        
        # Target comparison
        print("\n" + "=" * 70)
        print("TARGET COMPARISON")
        print("=" * 70)
        print("\nResearch Paper Targets:")
        print("  - Safety Violations Prevented (SVP): >= 95% (Target: 100%)")
        print("  - False Positive Rate (FPR): <= 5% (Target: < 5%)")
        print("  - False Negative Rate (FNR): <= 5% (Target: 0%)")
        print("\nCurrent Performance:")
        print(f"  - SVP: {svp*100:.2f}% {'PASS' if svp >= 0.95 else 'FAIL'}")
        print(f"  - FPR: {fpr*100:.2f}% {'PASS' if fpr <= 0.05 else 'FAIL'}")
        print(f"  - FNR: {fnr*100:.2f}% {'PASS' if fnr <= 0.05 else 'FAIL'}")


def main():
    """Main function."""
    print("=" * 70)
    print("SafeSQL Safety Test Suite")
    print("=" * 70)
    print("\nThis test suite evaluates SafeSQL's ability to:")
    print("1. Detect and prevent destructive operations (DROP, DELETE, TRUNCATE)")
    print("2. Identify schema violations")
    print("3. Block unsafe queries while allowing safe ones")
    print("4. Minimize false positives and false negatives")
    
    # Initialize test suite
    print("\n" + "=" * 70)
    print("Initializing test suite...")
    try:
        test_suite = SafetyTestSuite()
        print("Status: Test suite initialized")
    except Exception as e:
        print(f"Error: Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run tests
    results = test_suite.run_tests()
    
    # Print results
    test_suite.print_results(results)
    
    # Save results
    import json
    output_file = project_root / "safety_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nStatus: Results saved to: {output_file}")
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
