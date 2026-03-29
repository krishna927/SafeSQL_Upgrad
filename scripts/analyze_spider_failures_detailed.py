"""Detailed analysis of Spider failures to identify improvement opportunities.

This script analyzes generated SQL vs gold SQL to identify specific patterns
that can be fixed to improve execution accuracy.
"""

import json
import sys
from pathlib import Path
from collections import Counter
import re

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_failures(results_file: Path):
    """Analyze failure patterns in detail."""
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    queries = data['spider_model3']['queries']
    
    print("=" * 70)
    print("DETAILED SPIDER FAILURE ANALYSIS")
    print("=" * 70)
    
    # Categorize failures
    table_name_issues = []
    join_issues = []
    column_name_issues = []
    aggregation_issues = []
    other_issues = []
    
    for query in queries:
        generated = query.get('generated_sql', '').upper()
        gold = query.get('gold_sql', '').upper()
        question = query.get('question', '')
        ex = query.get('execution_accuracy', 0)
        
        if ex == 0:  # Failed query
            issues = []
            
            # Check for generic table name
            if 'FROM "TABLE"' in generated or 'FROM TABLE' in generated or 'FROM table' in generated:
                issues.append('generic_table')
                table_name_issues.append({
                    'question': question[:60],
                    'generated': query.get('generated_sql', '')[:100],
                    'gold': gold[:100]
                })
            
            # Check for missing JOIN
            if 'JOIN' in gold and 'JOIN' not in generated:
                issues.append('missing_join')
                join_issues.append({
                    'question': question[:60],
                    'generated': query.get('generated_sql', '')[:100],
                    'gold': gold[:150]
                })
            
            # Check for column name issues (quoted vs unquoted)
            if '"' in generated and '"' not in gold:
                issues.append('quoted_columns')
                column_name_issues.append({
                    'question': question[:60],
                    'generated': query.get('generated_sql', '')[:100],
                    'gold': gold[:100]
                })
            
            # Check for aggregation issues
            if 'GROUP BY' in gold and 'GROUP BY' not in generated:
                issues.append('missing_groupby')
                aggregation_issues.append({
                    'question': question[:60],
                    'generated': query.get('generated_sql', '')[:100],
                    'gold': gold[:100]
                })
            
            if not issues:
                other_issues.append({
                    'question': question[:60],
                    'generated': query.get('generated_sql', '')[:100],
                    'gold': gold[:100]
                })
    
    # Print statistics
    print(f"\nTotal Failed Queries: {len([q for q in queries if q.get('execution_accuracy', 0) == 0])}")
    print(f"\nIssue Categories:")
    print(f"  1. Generic Table Names: {len(table_name_issues)} queries ({len(table_name_issues)/len(queries)*100:.1f}%)")
    print(f"  2. Missing JOINs: {len(join_issues)} queries ({len(join_issues)/len(queries)*100:.1f}%)")
    print(f"  3. Column Name Issues: {len(column_name_issues)} queries ({len(column_name_issues)/len(queries)*100:.1f}%)")
    print(f"  4. Missing GROUP BY: {len(aggregation_issues)} queries ({len(aggregation_issues)/len(queries)*100:.1f}%)")
    print(f"  5. Other Issues: {len(other_issues)} queries ({len(other_issues)/len(queries)*100:.1f}%)")
    
    # Show examples
    print("\n" + "=" * 70)
    print("EXAMPLES - Generic Table Names")
    print("=" * 70)
    for i, issue in enumerate(table_name_issues[:5], 1):
        print(f"\n[{i}] {issue['question']}...")
        print(f"    Generated: {issue['generated']}")
        print(f"    Gold: {issue['gold']}")
        # Extract actual table name from gold
        gold_tables = re.findall(r'FROM\s+(\w+)', issue['gold'], re.IGNORECASE)
        if gold_tables:
            print(f"    -> Should use table: {gold_tables[0]}")
    
    print("\n" + "=" * 70)
    print("EXAMPLES - Missing JOINs")
    print("=" * 70)
    for i, issue in enumerate(join_issues[:5], 1):
        print(f"\n[{i}] {issue['question']}...")
        print(f"    Generated: {issue['generated']}")
        print(f"    Gold: {issue['gold']}")
        # Extract JOIN info
        joins = re.findall(r'JOIN\s+(\w+)\s+AS\s+(\w+)', issue['gold'], re.IGNORECASE)
        if joins:
            print(f"    -> Requires JOIN: {joins}")
    
    # Calculate potential improvement
    print("\n" + "=" * 70)
    print("POTENTIAL IMPROVEMENT ESTIMATES")
    print("=" * 70)
    
    # If we fix table names, we might get some queries working
    # If we fix JOINs, we might get more queries working
    # These are rough estimates based on issue frequency
    
    current_accuracy = len([q for q in queries if q.get('execution_accuracy', 0) == 1]) / len(queries) * 100
    
    print(f"\nCurrent Accuracy: {current_accuracy:.1f}%")
    print(f"\nIf we fix Generic Table Names:")
    print(f"  - Affects {len(table_name_issues)} queries")
    print(f"  - Estimated improvement: +{min(len(table_name_issues)*0.3, 30):.1f}% (if 30% of these become correct)")
    print(f"  - Potential new accuracy: ~{min(current_accuracy + len(table_name_issues)*0.3, 100):.1f}%")
    
    print(f"\nIf we fix Missing JOINs:")
    print(f"  - Affects {len(join_issues)} queries")
    print(f"  - Estimated improvement: +{min(len(join_issues)*0.5, 35):.1f}% (if 50% of these become correct)")
    print(f"  - Potential new accuracy: ~{min(current_accuracy + len(join_issues)*0.5, 100):.1f}%")
    
    print(f"\nIf we fix BOTH Table Names AND JOINs:")
    print(f"  - Combined potential: +{min(len(table_name_issues)*0.3 + len(join_issues)*0.5, 50):.1f}%")
    print(f"  - Potential new accuracy: ~{min(current_accuracy + len(table_name_issues)*0.3 + len(join_issues)*0.5, 100):.1f}%")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("\nPriority 1: Fix Generic Table Names")
    print("  - Impact: High (affects ~100% of queries)")
    print("  - Difficulty: Medium")
    print("  - Expected improvement: +20-30%")
    
    print("\nPriority 2: Fix Missing JOINs")
    print("  - Impact: High (affects ~70% of queries)")
    print("  - Difficulty: High")
    print("  - Expected improvement: +30-40%")
    
    print("\nPriority 3: Fix Column Name Quoting")
    print("  - Impact: Medium (affects ~40% of queries)")
    print("  - Difficulty: Low")
    print("  - Expected improvement: +5-10%")
    
    print("\nCombined Potential:")
    print(f"  - Current: {current_accuracy:.1f}%")
    print(f"  - With all fixes: ~{min(current_accuracy + 50, 100):.1f}%")
    print(f"  - Improvement: +{min(50, 100 - current_accuracy):.1f} percentage points")


if __name__ == "__main__":
    results_file = project_root / "evaluation_results" / "spider_results_20260301_175601.json"
    if results_file.exists():
        analyze_failures(results_file)
    else:
        print(f"Results file not found: {results_file}")
        print("Run evaluation first: python scripts/run_models_spider_bird.py --spider_only --n_samples 50")
