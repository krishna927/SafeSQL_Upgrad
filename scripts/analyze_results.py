"""Analyze evaluation results and provide summary."""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
results_dir = project_root / "evaluation_results"

# Find latest results file
result_files = list(results_dir.glob("spider_results_*.json"))
if not result_files:
    print("No results files found")
    sys.exit(1)

latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
print(f"Analyzing: {latest_file.name}\n")

with open(latest_file, 'r') as f:
    data = json.load(f)

m3 = data.get('spider_model3', {}).get('metrics', {})
m1 = data.get('spider_model1', {}).get('metrics', {})

print("=" * 70)
print("SPIDER DATASET EVALUATION RESULTS")
print("=" * 70)

print("\nModel 3 (Baseline GPT-4):")
print(f"  Execution Accuracy: {m3.get('execution_accuracy', 0):.2%}")
print(f"  Exact Match: {m3.get('exact_match', 0):.2%}")
print(f"  Successful Queries: {m3.get('successful', 0)}/{m3.get('total', 0)}")
print(f"  Failed Queries: {m3.get('failed', 0)}")

print("\nModel 1 (GPT-4 + SafeSQL):")
print(f"  Execution Accuracy: {m1.get('execution_accuracy', 0):.2%}")
print(f"  Exact Match: {m1.get('exact_match', 0):.2%}")
print(f"  Safety Violations Prevented: {m1.get('safety_violations_prevented', 0)}")
print(f"  Auto-Repair Success: {m1.get('auto_repair_success', 0)}")
print(f"  Successful Queries: {m1.get('successful', 0)}/{m1.get('total', 0)}")
print(f"  Failed Queries: {m1.get('failed', 0)}")

print("\n" + "=" * 70)
print("COMPARISON")
print("=" * 70)

ex_diff = m1.get('execution_accuracy', 0) - m3.get('execution_accuracy', 0)
em_diff = m1.get('exact_match', 0) - m3.get('exact_match', 0)

print(f"\nExecution Accuracy Difference: {ex_diff:+.2%}")
print(f"Exact Match Difference: {em_diff:+.2%}")

if m1.get('auto_repair_success', 0) > 0:
    repair_rate = m1.get('auto_repair_success', 0) / m1.get('total', 1)
    print(f"\nAuto-Repair Rate: {repair_rate:.2%}")

print("\n" + "=" * 70)
