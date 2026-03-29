"""Script to analyze datasets for EDA content generation."""
import json
from pathlib import Path
from collections import Counter
import statistics

def analyze_spider():
    """Analyze Spider dataset."""
    data_file = Path("data/datasets/spider/dev.json")
    if not data_file.exists():
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = {
        'total_queries': len(data),
        'unique_databases': len(set(s['db_id'] for s in data)),
        'question_lengths': [len(s['question']) for s in data],
        'sql_lengths': [len(s['query']) for s in data],
        'databases': list(set(s['db_id'] for s in data))
    }
    
    stats['avg_question_length'] = statistics.mean(stats['question_lengths'])
    stats['avg_sql_length'] = statistics.mean(stats['sql_lengths'])
    stats['median_question_length'] = statistics.median(stats['question_lengths'])
    stats['median_sql_length'] = statistics.median(stats['sql_lengths'])
    
    # Analyze query complexity (simple heuristics)
    query_types = []
    for s in data:
        sql = s['query'].upper()
        if 'JOIN' in sql:
            query_types.append('JOIN')
        elif 'GROUP BY' in sql:
            query_types.append('AGGREGATION')
        elif 'UNION' in sql or 'INTERSECT' in sql:
            query_types.append('SET_OPERATION')
        elif 'EXISTS' in sql or 'IN (' in sql:
            query_types.append('SUBQUERY')
        else:
            query_types.append('SIMPLE')
    
    stats['query_type_distribution'] = dict(Counter(query_types))
    
    return stats

def analyze_wikisql():
    """Analyze WikiSQL_VALUE dataset."""
    data_file = Path("data/datasets/wikisql_value/extracted/data/dev.jsonl")
    if not data_file.exists():
        return None
    
    data = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    
    stats = {
        'total_queries': len(data),
        'question_lengths': [len(s.get('question', '')) for s in data],
        'sql_lengths': [len(s.get('sql_string', '')) for s in data],
        'unique_tables': len(set(s.get('table_id', '').split('_')[0] for s in data if 'table_id' in s))
    }
    
    stats['avg_question_length'] = statistics.mean(stats['question_lengths'])
    stats['avg_sql_length'] = statistics.mean(stats['sql_lengths'])
    stats['median_question_length'] = statistics.median(stats['question_lengths'])
    stats['median_sql_length'] = statistics.median(stats['sql_lengths'])
    
    # Analyze query types
    query_types = []
    for s in data:
        sql = s.get('sql_string', '').upper()
        if 'GROUP BY' in sql or 'COUNT' in sql or 'SUM' in sql or 'AVG' in sql:
            query_types.append('AGGREGATION')
        elif 'WHERE' in sql:
            query_types.append('FILTER')
        else:
            query_types.append('SIMPLE')
    
    stats['query_type_distribution'] = dict(Counter(query_types))
    
    return stats

if __name__ == "__main__":
    print("=== DATASET ANALYSIS FOR EDA ===\n")
    
    spider_stats = analyze_spider()
    if spider_stats:
        print("SPIDER DATASET:")
        print(f"  Total queries: {spider_stats['total_queries']}")
        print(f"  Unique databases: {spider_stats['unique_databases']}")
        print(f"  Avg question length: {spider_stats['avg_question_length']:.1f} chars")
        print(f"  Avg SQL length: {spider_stats['avg_sql_length']:.1f} chars")
        print(f"  Query type distribution: {spider_stats['query_type_distribution']}")
        print()
    
    wikisql_stats = analyze_wikisql()
    if wikisql_stats:
        print("WIKISQL_VALUE DATASET:")
        print(f"  Total queries: {wikisql_stats['total_queries']}")
        print(f"  Unique tables: {wikisql_stats['unique_tables']}")
        print(f"  Avg question length: {wikisql_stats['avg_question_length']:.1f} chars")
        print(f"  Avg SQL length: {wikisql_stats['avg_sql_length']:.1f} chars")
        print(f"  Query type distribution: {wikisql_stats['query_type_distribution']}")
        print()
    
    # Save to JSON for later use
    output = {
        'spider': spider_stats,
        'wikisql_value': wikisql_stats
    }
    
    with open('analysis_output/dataset_stats_for_eda.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("Stats saved to: analysis_output/dataset_stats_for_eda.json")
