"""Generate charts for Chapter 4: Analysis and Implementation.

This script creates visualizations of WikiSQL_VALUE dataset analysis
for inclusion in the research document.
"""

import json
import sys
from pathlib import Path
from collections import Counter
import statistics
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving files

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader

# Set style for professional academic charts
plt.style.use('seaborn-v0_8-whitegrid')
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['axes.labelsize'] = 12
matplotlib.rcParams['axes.titlesize'] = 13
matplotlib.rcParams['xtick.labelsize'] = 10
matplotlib.rcParams['ytick.labelsize'] = 10
matplotlib.rcParams['legend.fontsize'] = 10
matplotlib.rcParams['figure.titlesize'] = 14

def generate_question_length_distribution(loader, output_dir):
    """Generate question length distribution chart."""
    print("Generating question length distribution chart...")
    
    train_queries = loader.load_queries("train")
    dev_queries = loader.load_queries("dev")
    test_queries = loader.load_queries("test")
    all_queries = train_queries + dev_queries + test_queries
    
    question_lengths = [len(q['question'].split()) for q in all_queries]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Histogram
    n, bins, patches = ax.hist(question_lengths, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
    
    # Add vertical lines for mean and median
    mean_len = statistics.mean(question_lengths)
    median_len = statistics.median(question_lengths)
    ax.axvline(mean_len, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_len:.2f} words')
    ax.axvline(median_len, color='green', linestyle='--', linewidth=2, label=f'Median: {median_len:.1f} words')
    
    ax.set_xlabel('Question Length (words)', fontweight='bold')
    ax.set_ylabel('Frequency', fontweight='bold')
    ax.set_title('Distribution of Natural Language Question Lengths in WikiSQL_VALUE Dataset', fontweight='bold', pad=15)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add statistics text box
    stats_text = f'Total Queries: {len(all_queries):,}\n'
    stats_text += f'Mean: {mean_len:.2f} words\n'
    stats_text += f'Median: {median_len:.1f} words\n'
    stats_text += f'Std Dev: {statistics.stdev(question_lengths):.2f} words\n'
    stats_text += f'Min: {min(question_lengths)} words\n'
    stats_text += f'Max: {max(question_lengths)} words'
    
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    output_path = output_dir / "figure_4_1_question_length_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def generate_aggregation_distribution(loader, output_dir):
    """Generate aggregation function distribution chart."""
    print("Generating aggregation function distribution chart...")
    
    train_queries = loader.load_queries("train")
    dev_queries = loader.load_queries("dev")
    test_queries = loader.load_queries("test")
    all_queries = train_queries + dev_queries + test_queries
    
    aggregation_types = Counter()
    for q in all_queries:
        sql = q.get('sql', {})
        agg = sql.get('agg', 0)
        aggregation_types[agg] += 1
    
    agg_names = {0: "None", 1: "MAX", 2: "MIN", 3: "COUNT", 4: "SUM", 5: "AVG"}
    
    # Prepare data
    labels = [agg_names.get(agg_val, f'Unknown({agg_val})') for agg_val in sorted(aggregation_types.keys())]
    counts = [aggregation_types[agg_val] for agg_val in sorted(aggregation_types.keys())]
    percentages = [(count / len(all_queries)) * 100 for count in counts]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Bar chart
    colors = ['steelblue', 'lightcoral', 'lightgreen', 'gold', 'plum', 'lightblue']
    bars = ax1.bar(labels, counts, color=colors[:len(labels)], edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Aggregation Function', fontweight='bold')
    ax1.set_ylabel('Number of Queries', fontweight='bold')
    ax1.set_title('Aggregation Function Distribution (Count)', fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, count, pct in zip(bars, counts, percentages):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Pie chart
    ax2.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90,
            colors=colors[:len(labels)], textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax2.set_title('Aggregation Function Distribution (Percentage)', fontweight='bold', pad=15)
    
    plt.suptitle('Distribution of Aggregation Functions in WikiSQL_VALUE Dataset', 
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / "figure_4_2_aggregation_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def generate_condition_count_distribution(loader, output_dir):
    """Generate WHERE clause condition count distribution chart."""
    print("Generating condition count distribution chart...")
    
    train_queries = loader.load_queries("train")
    dev_queries = loader.load_queries("dev")
    test_queries = loader.load_queries("test")
    all_queries = train_queries + dev_queries + test_queries
    
    condition_counts = []
    for q in all_queries:
        sql = q.get('sql', {})
        conds = sql.get('conds', [])
        condition_counts.append(len(conds))
    
    condition_dist = Counter(condition_counts)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Bar chart
    labels = [str(i) for i in sorted(condition_dist.keys())]
    counts = [condition_dist[i] for i in sorted(condition_dist.keys())]
    percentages = [(count / len(all_queries)) * 100 for count in counts]
    
    bars = ax.bar(labels, counts, color='steelblue', edgecolor='black', alpha=0.7)
    ax.set_xlabel('Number of Conditions in WHERE Clause', fontweight='bold')
    ax.set_ylabel('Number of Queries', fontweight='bold')
    ax.set_title('Distribution of WHERE Clause Condition Counts in WikiSQL_VALUE Dataset', 
                 fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar, count, pct in zip(bars, counts, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add statistics
    queries_with_where = sum(1 for c in condition_counts if c > 0)
    stats_text = f'Total Queries: {len(all_queries):,}\n'
    stats_text += f'Queries with WHERE: {queries_with_where:,} ({queries_with_where/len(all_queries)*100:.1f}%)\n'
    stats_text += f'Mean Conditions: {statistics.mean(condition_counts):.2f}\n'
    stats_text += f'Median Conditions: {statistics.median(condition_counts):.1f}\n'
    stats_text += f'Max Conditions: {max(condition_counts)}'
    
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    output_path = output_dir / "figure_4_3_condition_count_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def generate_table_schema_characteristics(loader, output_dir):
    """Generate table schema characteristics chart."""
    print("Generating table schema characteristics chart...")
    
    train_tables = loader.load_tables("train")
    dev_tables = loader.load_tables("dev")
    test_tables = loader.load_tables("test")
    all_tables = {**train_tables, **dev_tables, **test_tables}
    
    column_counts = []
    for table_id, table_data in list(all_tables.items())[:1000]:  # Sample first 1000
        header = table_data.get('header', [])
        column_counts.append(len(header))
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Histogram
    n, bins, patches = ax.hist(column_counts, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
    
    # Add vertical lines for mean and median
    mean_cols = statistics.mean(column_counts)
    median_cols = statistics.median(column_counts)
    ax.axvline(mean_cols, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_cols:.2f} columns')
    ax.axvline(median_cols, color='green', linestyle='--', linewidth=2, label=f'Median: {median_cols:.1f} columns')
    
    ax.set_xlabel('Number of Columns per Table', fontweight='bold')
    ax.set_ylabel('Frequency', fontweight='bold')
    ax.set_title('Distribution of Table Schema Sizes in WikiSQL_VALUE Dataset', fontweight='bold', pad=15)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add statistics
    stats_text = f'Sample Size: {len(column_counts)} tables\n'
    stats_text += f'Total Tables: {len(all_tables):,}\n'
    stats_text += f'Mean Columns: {mean_cols:.2f}\n'
    stats_text += f'Median Columns: {median_cols:.1f}\n'
    stats_text += f'Min Columns: {min(column_counts)}\n'
    stats_text += f'Max Columns: {max(column_counts)}'
    
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    output_path = output_dir / "figure_4_4_table_schema_characteristics.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def generate_dataset_split_distribution(loader, output_dir):
    """Generate dataset split distribution chart."""
    print("Generating dataset split distribution chart...")
    
    train_queries = loader.load_queries("train")
    dev_queries = loader.load_queries("dev")
    test_queries = loader.load_queries("test")
    
    splits = ['Train', 'Dev', 'Test']
    counts = [len(train_queries), len(dev_queries), len(test_queries)]
    colors = ['steelblue', 'lightcoral', 'lightgreen']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Bar chart
    bars = ax1.bar(splits, counts, color=colors, edgecolor='black', alpha=0.7)
    ax1.set_ylabel('Number of Queries', fontweight='bold')
    ax1.set_title('Dataset Split Distribution (Count)', fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    total = sum(counts)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        pct = (count / total) * 100
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Pie chart
    ax2.pie(counts, labels=splits, autopct='%1.1f%%', startangle=90,
            colors=colors, textprops={'fontsize': 11, 'fontweight': 'bold'})
    ax2.set_title('Dataset Split Distribution (Percentage)', fontweight='bold', pad=15)
    
    plt.suptitle('WikiSQL_VALUE Dataset Split Distribution', 
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / "figure_4_5_dataset_split_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def generate_dialectal_variants_comparison(loader, output_dir):
    """Generate dialectal variants comparison chart."""
    print("Generating dialectal variants comparison chart...")
    
    dialects = ['AppE', 'ChcE', 'CollSgE', 'IndE', 'MULTI', 'UAAVE']
    dialect_counts = []
    
    for dialect in dialects:
        try:
            dev_dialect = loader.load_queries("dev", dialect=dialect)
            dialect_counts.append(len(dev_dialect))
        except:
            dialect_counts.append(0)
    
    # Also get standard count
    standard_count = len(loader.load_queries("dev"))
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Bar chart
    all_labels = ['Standard'] + dialects
    all_counts = [standard_count] + dialect_counts
    colors = ['steelblue'] + ['lightcoral', 'lightgreen', 'gold', 'plum', 'lightblue', 'orange']
    
    bars = ax.bar(all_labels, all_counts, color=colors[:len(all_labels)], edgecolor='black', alpha=0.7)
    ax.set_ylabel('Number of Queries (Dev Split)', fontweight='bold')
    ax.set_xlabel('Dialectal Variant', fontweight='bold')
    ax.set_title('Dialectal Variants Distribution in WikiSQL_VALUE Dataset', fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar, count in zip(bars, all_counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add note
    ax.text(0.5, 0.02, 'Note: Each dialectal variant contains the same number of queries as the standard split',
            transform=ax.transAxes, fontsize=9, ha='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    output_path = output_dir / "figure_4_6_dialectal_variants_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()

def main():
    """Generate all charts for Chapter 4."""
    print("=" * 70)
    print("Generating Charts for Chapter 4: Analysis and Implementation")
    print("=" * 70)
    
    # Create output directory
    output_dir = project_root / "docs" / "chapter4_figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}\n")
    
    # Initialize loader
    try:
        loader = WikiSQLValueLoader()
        print("WikiSQL_VALUE loader initialized successfully\n")
    except Exception as e:
        print(f"Error initializing loader: {e}")
        return
    
    # Generate all charts
    try:
        generate_question_length_distribution(loader, output_dir)
        generate_aggregation_distribution(loader, output_dir)
        generate_condition_count_distribution(loader, output_dir)
        generate_table_schema_characteristics(loader, output_dir)
        generate_dataset_split_distribution(loader, output_dir)
        generate_dialectal_variants_comparison(loader, output_dir)
        
        print("\n" + "=" * 70)
        print("All charts generated successfully!")
        print("=" * 70)
        print(f"\nCharts saved to: {output_dir}")
        print("\nGenerated figures:")
        print("  - figure_4_1_question_length_distribution.png")
        print("  - figure_4_2_aggregation_distribution.png")
        print("  - figure_4_3_condition_count_distribution.png")
        print("  - figure_4_4_table_schema_characteristics.png")
        print("  - figure_4_5_dataset_split_distribution.png")
        print("  - figure_4_6_dialectal_variants_comparison.png")
        
    except Exception as e:
        print(f"\nError generating charts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
