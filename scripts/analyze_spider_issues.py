"""Analyze Spider dataset issues from existing evaluation results.

This script analyzes existing Spider evaluation results to identify
common failure patterns WITHOUT making any API calls.

Analyzes:
1. Common error types
2. Schema-related issues
3. SQL syntax errors
4. Join/relationship issues
5. Aggregation problems
"""

import json
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_spider_results(results_file: Path) -> Dict:
    """Analyze Spider evaluation results."""
    print(f"Loading results from: {results_file}")
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find Spider results - handle different file structures
    spider_results = None
    
    # Try direct structure (spider_results_*.json)
    if 'spider_model3' in data:
        spider_results = data['spider_model3']
    elif 'spider_model1' in data:
        spider_results = data['spider_model1']
    # Try nested structure (combined_results_*.json)
    elif 'results' in data:
        for key in ['spider_model1', 'spider_model3']:
            if key in data['results']:
                spider_results = data['results'][key]
                break
    
    if not spider_results:
        print("No Spider results found in file")
        print(f"Available keys: {list(data.keys())[:10]}")
        return {}
    
    queries = spider_results.get('queries', [])
    print(f"\nAnalyzing {len(queries)} queries...")
    
    # Categorize queries
    successful = []
    failed = []
    errors = []
    execution_errors = []
    syntax_errors = []
    schema_errors = []
    
    for query in queries:
        ex = query.get('execution_accuracy', 0)
        status = query.get('status', 'unknown')
        
        if ex == 1.0:
            successful.append(query)
        else:
            failed.append(query)
            
            # Analyze errors
            error_msg = query.get('error', '')
            if error_msg:
                errors.append(error_msg.lower())
            
            # Check verification errors
            verification = query.get('verification', {})
            if verification:
                validation = verification.get('validation_results', {})
                schema_validation = validation.get('schema', {})
                if not schema_validation.get('valid', True):
                    schema_errors.append(query)
            
            # Categorize error types
            error_lower = error_msg.lower()
            if 'syntax' in error_lower or 'sql' in error_lower:
                syntax_errors.append(query)
            if 'no such column' in error_lower or 'no such table' in error_lower:
                schema_errors.append(query)
            if 'execution' in error_lower or 'execute' in error_lower:
                execution_errors.append(query)
    
    # Analyze common patterns
    error_patterns = Counter(errors)
    
    # Analyze SQL differences
    sql_issues = []
    for query in failed[:10]:  # Analyze first 10 failures
        generated = query.get('generated_sql', '')
        gold = query.get('gold_sql', '')
        
        if generated and gold:
            # Check for common differences
            issues = []
            if 'JOIN' in gold and 'JOIN' not in generated:
                issues.append("Missing JOIN")
            if 'GROUP BY' in gold and 'GROUP BY' not in generated:
                issues.append("Missing GROUP BY")
            if 'ORDER BY' in gold and 'ORDER BY' not in generated:
                issues.append("Missing ORDER BY")
            if 'COUNT(' in gold and 'COUNT(' not in generated:
                issues.append("Missing COUNT")
            if 'WHERE' in gold and 'WHERE' not in generated:
                issues.append("Missing WHERE")
            
            if issues:
                sql_issues.append({
                    'question': query.get('question', '')[:60],
                    'issues': issues,
                    'generated': generated[:100],
                    'gold': gold[:100]
                })
    
    return {
        'total': len(queries),
        'successful': len(successful),
        'failed': len(failed),
        'success_rate': len(successful) / len(queries) * 100 if queries else 0,
        'error_patterns': dict(error_patterns.most_common(10)),
        'schema_errors': len(schema_errors),
        'syntax_errors': len(syntax_errors),
        'execution_errors': len(execution_errors),
        'sql_issues': sql_issues,
        'sample_failures': [
            {
                'question': q.get('question', '')[:80],
                'error': q.get('error', '')[:100],
                'generated_sql': q.get('generated_sql', '')[:100]
            }
            for q in failed[:5]
        ]
    }


def main():
    """Run Spider issue analysis."""
    print("=" * 70)
    print("Spider Dataset Issue Analysis")
    print("=" * 70)
    print("\nNOTE: This script analyzes existing results - NO API calls!")
    print("=" * 70)
    
    # Find latest Spider results
    results_dir = project_root / "evaluation_results"
    spider_files = list(results_dir.glob("spider_results_*.json"))
    
    if not spider_files:
        print("\nNo Spider results files found!")
        print("Run evaluation first: python scripts/run_models_spider_bird.py --spider_only --n_samples 50")
        return
    
    # Use latest file
    latest_file = max(spider_files, key=lambda p: p.stat().st_mtime)
    print(f"\nAnalyzing: {latest_file.name}")
    
    analysis = analyze_spider_results(latest_file)
    
    print("\n" + "=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    
    print(f"\nOverall Statistics:")
    print(f"  Total queries: {analysis['total']}")
    print(f"  Successful: {analysis['successful']} ({analysis['success_rate']:.1f}%)")
    print(f"  Failed: {analysis['failed']} ({100 - analysis['success_rate']:.1f}%)")
    
    print(f"\nError Categories:")
    print(f"  Schema errors: {analysis['schema_errors']}")
    print(f"  Syntax errors: {analysis['syntax_errors']}")
    print(f"  Execution errors: {analysis['execution_errors']}")
    
    if analysis['error_patterns']:
        print(f"\nTop Error Patterns:")
        for pattern, count in list(analysis['error_patterns'].items())[:5]:
            print(f"  - {pattern[:60]}: {count}")
    
    if analysis['sql_issues']:
        print(f"\nCommon SQL Issues (from first 10 failures):")
        for issue in analysis['sql_issues'][:5]:
            print(f"\n  Question: {issue['question']}...")
            print(f"  Issues: {', '.join(issue['issues'])}")
            print(f"  Generated: {issue['generated']}...")
            print(f"  Gold: {issue['gold']}...")
    
    if analysis['sample_failures']:
        print(f"\nSample Failures:")
        for i, failure in enumerate(analysis['sample_failures'], 1):
            print(f"\n  [{i}] {failure['question']}...")
            if failure['error']:
                print(f"      Error: {failure['error']}...")
            if failure['generated_sql']:
                print(f"      Generated SQL: {failure['generated_sql']}...")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    recommendations = []
    
    if analysis['schema_errors'] > analysis['total'] * 0.3:
        recommendations.append("High schema error rate - check column/table name mapping")
    
    if analysis['syntax_errors'] > analysis['total'] * 0.2:
        recommendations.append("High syntax error rate - improve SQL generation prompts")
    
    if any('join' in str(issue['issues']).lower() for issue in analysis['sql_issues']):
        recommendations.append("Missing JOINs detected - enhance join detection in prompts")
    
    if any('group by' in str(issue['issues']).lower() for issue in analysis['sql_issues']):
        recommendations.append("Missing GROUP BY detected - improve aggregation handling")
    
    if not recommendations:
        recommendations.append("No specific patterns identified - investigate individual failures")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
