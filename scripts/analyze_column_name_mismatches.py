"""Analyze column name mismatches in Spider results.

This script analyzes failed queries to identify column name patterns.
"""

import json
from pathlib import Path
import re
from collections import defaultdict

project_root = Path(__file__).parent.parent
results_file = project_root / "evaluation_results" / "spider_results_20260301_181920.json"

with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

model3_results = data.get("spider_model3", {}).get("queries", [])

# Analyze failures
failures = []
column_patterns = defaultdict(int)

for result in model3_results:
    if result.get("execution_accuracy", 0) == 0.0:
        generated = result.get("generated_sql", "")
        gold = result.get("gold_sql", "")
        
        # Extract column names from generated SQL (quoted)
        generated_cols = re.findall(r'["\']([^"\']+)["\']', generated)
        
        # Extract column names from gold SQL (unquoted)
        gold_cols = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', gold)
        
        failures.append({
            'question': result.get("question", "")[:60],
            'generated': generated[:100],
            'gold': gold[:100],
            'generated_cols': generated_cols[:5],
            'gold_cols': gold_cols[:5]
        })
        
        # Count patterns
        if generated_cols:
            for col in generated_cols[:3]:
                column_patterns[col.lower()] += 1

print("=" * 70)
print("Column Name Mismatch Analysis")
print("=" * 70)
print(f"\nTotal failures: {len(failures)}")
print(f"\nTop column name patterns in generated SQL:")
for col, count in sorted(column_patterns.items(), key=lambda x: -x[1])[:10]:
    print(f"  '{col}': {count}")

print("\n" + "=" * 70)
print("Sample Failures:")
print("=" * 70)
for i, fail in enumerate(failures[:5], 1):
    print(f"\n--- Failure {i} ---")
    print(f"Question: {fail['question']}...")
    print(f"Generated cols: {fail['generated_cols']}")
    print(f"Gold cols: {fail['gold_cols']}")
    print(f"Generated SQL: {fail['generated'][:80]}...")
    print(f"Gold SQL: {fail['gold'][:80]}...")
