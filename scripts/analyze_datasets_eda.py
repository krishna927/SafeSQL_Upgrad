"""Comprehensive EDA analysis of datasets for Chapter 4."""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
from src.data.loaders.spider_loader import SpiderLoader

def analyze_wikisql_value():
    """Analyze WikiSQL_VALUE dataset."""
    print("=" * 70)
    print("WIKISQL_VALUE DATASET ANALYSIS")
    print("=" * 70)
    
    loader = WikiSQLValueLoader()
    
    # Load all splits
    train_queries = loader.load_queries("train")
    dev_queries = loader.load_queries("dev")
    test_queries = loader.load_queries("test")
    
    print(f"\nDataset Size:")
    print(f"  Train: {len(train_queries):,} queries")
    print(f"  Dev: {len(dev_queries):,} queries")
    print(f"  Test: {len(test_queries):,} queries")
    print(f"  Total: {len(train_queries) + len(dev_queries) + len(test_queries):,} queries")
    
    # Load tables
    train_tables = loader.load_tables("train")
    dev_tables = loader.load_tables("dev")
    test_tables = loader.load_tables("test")
    
    all_tables = {**train_tables, **dev_tables, **test_tables}
    print(f"\nTables:")
    print(f"  Unique tables: {len(all_tables):,}")
    
    # Analyze query characteristics
    all_queries = train_queries + dev_queries + test_queries
    
    # Question length analysis
    question_lengths = [len(q['question'].split()) for q in all_queries]
    print(f"\nQuestion Length Statistics:")
    print(f"  Mean: {statistics.mean(question_lengths):.2f} words")
    print(f"  Median: {statistics.median(question_lengths):.2f} words")
    print(f"  Min: {min(question_lengths)} words")
    print(f"  Max: {max(question_lengths)} words")
    print(f"  Std Dev: {statistics.stdev(question_lengths):.2f} words")
    
    # SQL structure analysis
    aggregation_types = Counter()
    condition_counts = []
    selected_column_counts = []
    
    for q in all_queries:
        sql = q.get('sql', {})
        agg = sql.get('agg', 0)
        aggregation_types[agg] += 1
        
        conds = sql.get('conds', [])
        condition_counts.append(len(conds))
        
        sel = sql.get('sel', 0)
        selected_column_counts.append(sel)
    
    print(f"\nAggregation Distribution:")
    agg_names = {0: "None", 1: "MAX", 2: "MIN", 3: "COUNT", 4: "SUM", 5: "AVG"}
    for agg_val, count in aggregation_types.most_common():
        pct = (count / len(all_queries)) * 100
        print(f"  {agg_names.get(agg_val, f'Unknown({agg_val})')}: {count:,} ({pct:.1f}%)")
    
    print(f"\nCondition Count Statistics:")
    print(f"  Mean: {statistics.mean(condition_counts):.2f} conditions")
    print(f"  Median: {statistics.median(condition_counts):.2f} conditions")
    print(f"  Max: {max(condition_counts)} conditions")
    print(f"  Queries with WHERE: {sum(1 for c in condition_counts if c > 0):,} ({sum(1 for c in condition_counts if c > 0)/len(condition_counts)*100:.1f}%)")
    
    # Table schema analysis
    column_counts = []
    for table_id, table_data in list(all_tables.items())[:1000]:  # Sample first 1000
        header = table_data.get('header', [])
        column_counts.append(len(header))
    
    if column_counts:
        print(f"\nTable Schema Statistics (sample of {len(column_counts)} tables):")
        print(f"  Mean columns: {statistics.mean(column_counts):.2f}")
        print(f"  Median columns: {statistics.median(column_counts):.2f}")
        print(f"  Min columns: {min(column_counts)}")
        print(f"  Max columns: {max(column_counts)}")
    
    # Dialectal variants
    print(f"\nDialectal Variants:")
    dialects = ['AppE', 'ChcE', 'CollSgE', 'IndE', 'MULTI', 'UAAVE']
    for dialect in dialects:
        try:
            dev_dialect = loader.load_queries("dev", dialect=dialect)
            print(f"  {dialect}: {len(dev_dialect):,} queries (dev split)")
        except:
            pass
    
    return {
        'total_queries': len(all_queries),
        'unique_tables': len(all_tables),
        'question_length_mean': statistics.mean(question_lengths),
        'question_length_std': statistics.stdev(question_lengths),
        'aggregation_distribution': dict(aggregation_types),
        'avg_conditions': statistics.mean(condition_counts),
        'queries_with_where': sum(1 for c in condition_counts if c > 0),
        'avg_columns_per_table': statistics.mean(column_counts) if column_counts else 0
    }

def analyze_spider():
    """Analyze Spider dataset if available."""
    print("\n" + "=" * 70)
    print("SPIDER DATASET ANALYSIS")
    print("=" * 70)
    
    try:
        loader = SpiderLoader()
        
        # Load queries
        train_queries = loader.load_queries("train")
        dev_queries = loader.load_queries("dev")
        
        print(f"\nDataset Size:")
        print(f"  Train: {len(train_queries):,} queries")
        print(f"  Dev: {len(dev_queries):,} queries")
        print(f"  Total: {len(train_queries) + len(dev_queries):,} queries")
        
        # Load tables
        tables = loader.load_tables()
        print(f"\nDatabases: {len(tables):,}")
        
        # Analyze database characteristics
        table_counts = []
        column_counts = []
        foreign_key_counts = []
        
        for db_id, db_info in list(tables.items())[:50]:  # Sample first 50
            table_names = db_info.get('table_names', [])
            table_counts.append(len(table_names))
            
            column_names = db_info.get('column_names', [])
            # Count actual columns (excluding special marker [-1, '*'])
            actual_columns = [c for c in column_names if c[0] != -1]
            column_counts.append(len(actual_columns))
            
            foreign_keys = db_info.get('foreign_keys', [])
            foreign_key_counts.append(len(foreign_keys))
        
        if table_counts:
            print(f"\nDatabase Structure Statistics (sample of {len(table_counts)} databases):")
            print(f"  Mean tables per database: {statistics.mean(table_counts):.2f}")
            print(f"  Mean columns per database: {statistics.mean(column_counts):.2f}")
            print(f"  Mean foreign keys per database: {statistics.mean(foreign_key_counts):.2f}")
        
        # Query complexity
        all_queries = train_queries + dev_queries
        question_lengths = [len(q['question'].split()) for q in all_queries]
        
        print(f"\nQuestion Length Statistics:")
        print(f"  Mean: {statistics.mean(question_lengths):.2f} words")
        print(f"  Median: {statistics.median(question_lengths):.2f} words")
        print(f"  Std Dev: {statistics.stdev(question_lengths):.2f} words")
        
        # SQL operation types (from SQL strings)
        operation_types = Counter()
        for q in all_queries[:1000]:  # Sample
            sql = q.get('query', q.get('sql', ''))
            if isinstance(sql, str):
                sql_upper = sql.upper().strip()
                if sql_upper.startswith('SELECT'):
                    operation_types['SELECT'] += 1
                elif sql_upper.startswith('INSERT'):
                    operation_types['INSERT'] += 1
                elif sql_upper.startswith('UPDATE'):
                    operation_types['UPDATE'] += 1
                elif sql_upper.startswith('DELETE'):
                    operation_types['DELETE'] += 1
        
        print(f"\nSQL Operation Types (sample of {sum(operation_types.values())} queries):")
        for op, count in operation_types.most_common():
            pct = (count / sum(operation_types.values())) * 100 if operation_types else 0
            print(f"  {op}: {count} ({pct:.1f}%)")
        
        return {
            'total_queries': len(all_queries),
            'databases': len(tables),
            'avg_tables_per_db': statistics.mean(table_counts) if table_counts else 0,
            'avg_columns_per_db': statistics.mean(column_counts) if column_counts else 0,
            'question_length_mean': statistics.mean(question_lengths),
            'operation_distribution': dict(operation_types)
        }
        
    except Exception as e:
        print(f"\nSpider dataset not available: {e}")
        print("  Note: Spider dataset needs to be downloaded separately")
        return None

def main():
    """Run comprehensive EDA analysis."""
    print("=" * 70)
    print("COMPREHENSIVE DATASET EDA FOR CHAPTER 4")
    print("=" * 70)
    
    wikisql_stats = analyze_wikisql_value()
    spider_stats = analyze_spider()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nWikiSQL_VALUE:")
    print(f"  Total queries: {wikisql_stats['total_queries']:,}")
    print(f"  Unique tables: {wikisql_stats['unique_tables']:,}")
    print(f"  Avg question length: {wikisql_stats['question_length_mean']:.2f} words")
    
    if spider_stats:
        print(f"\nSpider:")
        print(f"  Total queries: {spider_stats['total_queries']:,}")
        print(f"  Databases: {spider_stats['databases']:,}")
        print(f"  Avg question length: {spider_stats['question_length_mean']:.2f} words")
    else:
        print(f"\nSpider: Dataset not available")
    
    print(f"\nBIRD: Dataset not yet downloaded")
    
    # Save results
    results = {
        'wikisql_value': wikisql_stats,
        'spider': spider_stats,
        'bird': None
    }
    
    output_file = project_root / "dataset_eda_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
