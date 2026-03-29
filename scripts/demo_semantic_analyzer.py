"""Demo script to show Semantic Analyzer in action.

This demonstrates:
1. How Semantic Analyzer compares generated SQL with gold standard
2. Semantic score calculation
3. Question intent matching
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.verification.semantic_analyzer import SemanticAnalyzer
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Demo Semantic Analyzer."""
    print("=" * 70)
    print("Semantic Analyzer - DEMO")
    print("=" * 70)
    print("\nThis demonstrates how Semantic Analyzer validates:")
    print("- SQL structure matches gold standard")
    print("- Selected columns match question intent")
    print("- Conditions match question requirements")
    print("- Aggregation types are correct\n")
    
    # Initialize components
    print("Step 1: Loading data and initializing analyzer...")
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    analyzer = SemanticAnalyzer()
    print("   Status: All components initialized\n")
    
    # Get sample queries
    print("Step 2: Loading sample queries...")
    samples = loader.get_sample("dev", n=5)
    print(f"   Status: Loaded {len(samples)} sample queries\n")
    
    print("=" * 70)
    print("SEMANTIC ANALYSIS RESULTS")
    print("=" * 70)
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\n--- Query {i} ---")
        print(f"Question: {question}")
        print(f"Gold SQL structure:")
        print(f"  - Selected column index: {gold_sql.get('sel')}")
        print(f"  - Aggregation: {gold_sql.get('agg')} "
              f"(0=None, 1=MAX, 2=MIN, 3=COUNT, 4=SUM, 5=AVG)")
        print(f"  - Conditions: {len(gold_sql.get('conds', []))} condition(s)")
        
        # Analyze with gold SQL (should be perfect match)
        result = analyzer.analyze(gold_sql, gold_sql, question, schema)
        
        print(f"\nAnalysis: Comparing gold SQL with itself")
        print(f"  Correct: {result['correct']}")
        print(f"  Semantic Score: {result['semantic_score']:.2f}/1.0")
        print(f"  Details:")
        print(f"    - Selected column match: {result['details']['selected_column_match']}")
        print(f"    - Conditions match: {result['details']['conditions_match']}")
        print(f"    - Aggregation match: {result['details']['aggregation_match']}")
        print(f"    - Question intent match: {result['details']['question_intent_match']}")
        
        if result['differences']:
            print(f"  Differences:")
            for diff in result['differences']:
                print(f"    - {diff}")
    
    # Test with intentionally modified SQL
    print("\n" + "=" * 70)
    print("TESTING WITH MODIFIED SQL")
    print("=" * 70)
    
    if samples:
        sample = samples[0]
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"\nQuestion: {question}")
        print(f"Gold SQL: sel={gold_sql.get('sel')}, agg={gold_sql.get('agg')}, "
              f"conds={len(gold_sql.get('conds', []))}")
        
        # Test 1: Wrong aggregation
        modified_sql1 = gold_sql.copy()
        original_agg = modified_sql1.get('agg', 0)
        modified_sql1['agg'] = 3 if original_agg == 0 else 0
        
        print(f"\n--- Modified SQL 1: Changed aggregation ---")
        print(f"  Original agg: {original_agg}, Modified agg: {modified_sql1['agg']}")
        result1 = analyzer.analyze(modified_sql1, gold_sql, question, schema)
        print(f"  Score: {result1['semantic_score']:.2f}/1.0, Correct: {result1['correct']}")
        if result1['differences']:
            print(f"  Differences:")
            for diff in result1['differences']:
                print(f"    - {diff}")
        
        # Test 2: Wrong selected column
        modified_sql2 = gold_sql.copy()
        original_sel = modified_sql2.get('sel', 0)
        # Change to different column (if available)
        columns = schema.get('columns', [])
        if len(columns) > 1:
            new_sel = (original_sel + 1) % len(columns)
            modified_sql2['sel'] = new_sel
            
            print(f"\n--- Modified SQL 2: Changed selected column ---")
            print(f"  Original sel: {original_sel}, Modified sel: {new_sel}")
            result2 = analyzer.analyze(modified_sql2, gold_sql, question, schema)
            print(f"  Score: {result2['semantic_score']:.2f}/1.0, Correct: {result2['correct']}")
            if result2['differences']:
                print(f"  Differences:")
                for diff in result2['differences']:
                    print(f"    - {diff}")
        
        # Test 3: Missing condition
        modified_sql3 = gold_sql.copy()
        original_conds = modified_sql3.get('conds', [])
        if len(original_conds) > 0:
            modified_sql3['conds'] = original_conds[:-1]  # Remove last condition
            
            print(f"\n--- Modified SQL 3: Removed condition ---")
            print(f"  Original conditions: {len(original_conds)}, "
                  f"Modified conditions: {len(modified_sql3['conds'])}")
            result3 = analyzer.analyze(modified_sql3, gold_sql, question, schema)
            print(f"  Score: {result3['semantic_score']:.2f}/1.0, Correct: {result3['correct']}")
            if result3['differences']:
                print(f"  Differences:")
                for diff in result3['differences']:
                    print(f"    - {diff}")
    
    print("\n" + "=" * 70)
    print("SEMANTIC ANALYZER COMPLETE")
    print("=" * 70)
    print("\nThe Semantic Analyzer validates that SQL matches question intent")
    print("and compares generated SQL with gold standard for correctness.")


if __name__ == "__main__":
    main()
