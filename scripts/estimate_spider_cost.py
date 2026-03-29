"""Estimate cost for running Spider dataset evaluation.

This script calculates the estimated API cost without making any API calls.
"""

# GPT-4 Pricing (as of 2025)
# Source: https://platform.openai.com/docs/pricing
GPT4_INPUT_COST_PER_MILLION = 30.00  # $30 per 1M input tokens
GPT4_OUTPUT_COST_PER_MILLION = 60.00  # $60 per 1M output tokens

# Token estimates per query (conservative)
# Based on typical schema + question + SQL response
ESTIMATED_INPUT_TOKENS_PER_QUERY = 800  # System prompt + user prompt + schema
ESTIMATED_OUTPUT_TOKENS_PER_QUERY = 100  # Generated SQL query

# Spider dataset size
SPIDER_DEV_QUERIES = 1034


def calculate_cost(n_queries: int, models: list = ['model3']) -> dict:
    """
    Calculate estimated cost for evaluation.
    
    Args:
        n_queries: Number of queries to evaluate
        models: List of models to run ('model1', 'model3', or both)
    
    Returns:
        Dictionary with cost breakdown
    """
    # Each model makes one API call per query
    n_api_calls = n_queries * len(models)
    
    # Calculate tokens
    total_input_tokens = n_api_calls * ESTIMATED_INPUT_TOKENS_PER_QUERY
    total_output_tokens = n_api_calls * ESTIMATED_OUTPUT_TOKENS_PER_QUERY
    
    # Calculate costs
    input_cost = (total_input_tokens / 1_000_000) * GPT4_INPUT_COST_PER_MILLION
    output_cost = (total_output_tokens / 1_000_000) * GPT4_OUTPUT_COST_PER_MILLION
    total_cost = input_cost + output_cost
    
    return {
        'n_queries': n_queries,
        'models': models,
        'n_api_calls': n_api_calls,
        'input_tokens': total_input_tokens,
        'output_tokens': total_output_tokens,
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_cost': total_cost,
        'cost_per_query': total_cost / n_queries if n_queries > 0 else 0
    }


def main():
    """Print cost estimates."""
    print("=" * 70)
    print("Spider Dataset Evaluation Cost Estimate")
    print("=" * 70)
    print(f"\nDataset: Spider dev set")
    print(f"Total queries: {SPIDER_DEV_QUERIES}")
    print(f"\nGPT-4 Pricing:")
    print(f"  Input:  ${GPT4_INPUT_COST_PER_MILLION:.2f} per 1M tokens")
    print(f"  Output: ${GPT4_OUTPUT_COST_PER_MILLION:.2f} per 1M tokens")
    print(f"\nToken Estimates per Query:")
    print(f"  Input:  ~{ESTIMATED_INPUT_TOKENS_PER_QUERY} tokens (prompt + schema)")
    print(f"  Output: ~{ESTIMATED_OUTPUT_TOKENS_PER_QUERY} tokens (SQL response)")
    
    print("\n" + "=" * 70)
    print("COST ESTIMATES")
    print("=" * 70)
    
    # Scenario 1: Model 3 only (Baseline)
    print("\n[Scenario 1] Model 3 Only (Baseline GPT-4)")
    print("-" * 70)
    cost1 = calculate_cost(SPIDER_DEV_QUERIES, ['model3'])
    print(f"  Queries: {cost1['n_queries']}")
    print(f"  API Calls: {cost1['n_api_calls']}")
    print(f"  Input Tokens: {cost1['input_tokens']:,} ({cost1['input_tokens']/1_000_000:.3f}M)")
    print(f"  Output Tokens: {cost1['output_tokens']:,} ({cost1['output_tokens']/1_000_000:.3f}M)")
    print(f"  Input Cost: ${cost1['input_cost']:.2f}")
    print(f"  Output Cost: ${cost1['output_cost']:.2f}")
    print(f"  TOTAL COST: ${cost1['total_cost']:.2f}")
    print(f"  Cost per Query: ${cost1['cost_per_query']:.4f}")
    
    # Scenario 2: Model 1 + Model 3
    print("\n[Scenario 2] Model 1 + Model 3 (Both)")
    print("-" * 70)
    cost2 = calculate_cost(SPIDER_DEV_QUERIES, ['model1', 'model3'])
    print(f"  Queries: {cost2['n_queries']}")
    print(f"  API Calls: {cost2['n_api_calls']}")
    print(f"  Input Tokens: {cost2['input_tokens']:,} ({cost2['input_tokens']/1_000_000:.3f}M)")
    print(f"  Output Tokens: {cost2['output_tokens']:,} ({cost2['output_tokens']/1_000_000:.3f}M)")
    print(f"  Input Cost: ${cost2['input_cost']:.2f}")
    print(f"  Output Cost: ${cost2['output_cost']:.2f}")
    print(f"  TOTAL COST: ${cost2['total_cost']:.2f}")
    print(f"  Cost per Query: ${cost2['cost_per_query']:.4f}")
    
    # Scenario 3: Sample (50 queries) - Model 3 only
    print("\n[Scenario 3] Sample Evaluation (50 queries) - Model 3 Only")
    print("-" * 70)
    cost3 = calculate_cost(50, ['model3'])
    print(f"  Queries: {cost3['n_queries']}")
    print(f"  API Calls: {cost3['n_api_calls']}")
    print(f"  TOTAL COST: ${cost3['total_cost']:.2f}")
    
    # Scenario 4: Sample (50 queries) - Both models
    print("\n[Scenario 4] Sample Evaluation (50 queries) - Model 1 + Model 3")
    print("-" * 70)
    cost4 = calculate_cost(50, ['model1', 'model3'])
    print(f"  Queries: {cost4['n_queries']}")
    print(f"  API Calls: {cost4['n_api_calls']}")
    print(f"  TOTAL COST: ${cost4['total_cost']:.2f}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print(f"\nCurrent API Budget: $1.00")
    print(f"\nFull Evaluation Costs:")
    print(f"  Model 3 only: ${cost1['total_cost']:.2f}")
    print(f"  Both models: ${cost2['total_cost']:.2f}")
    print(f"\n[WARNING] You will need to reload your account for full evaluation!")
    print(f"\nSample Evaluation Costs (50 queries):")
    print(f"  Model 3 only: ${cost3['total_cost']:.2f} [OK] Within budget")
    print(f"  Both models: ${cost4['total_cost']:.2f} [WARNING] Exceeds budget")
    
    print(f"\n[INFO] Cost-Saving Options:")
    print(f"  1. Use GPT-4o instead of GPT-4 (cheaper: $2.50/$10 per 1M tokens)")
    print(f"  2. Use GPT-4o-mini for testing ($0.15/$0.60 per 1M tokens)")
    print(f"  3. Use Model 2 (LLaMA-3) via Groq API (FREE)")
    print(f"  4. Run sample evaluation first (50 queries)")
    
    print("\n" + "=" * 70)
    print("\nNote: These are estimates. Actual costs may vary based on:")
    print("  - Actual token usage (schema complexity, query length)")
    print("  - Rate limiting (may require retries)")
    print("  - Failed queries (retries)")
    print("  - Model choice (GPT-4 vs GPT-4o vs GPT-4o-mini)")
    print("=" * 70)


if __name__ == "__main__":
    main()
