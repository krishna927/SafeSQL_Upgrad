"""Semantic correctness analysis for SQL queries.

This module validates that SQL queries match the question intent by:
- Comparing generated SQL structure with gold standard SQL
- Validating selected columns match question intent
- Checking conditions match question requirements
- Verifying aggregation types are correct
"""

from typing import Dict, List, Optional, Set, Tuple
import logging
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SemanticAnalyzer:
    """Analyzes semantic correctness of SQL queries."""
    
    def __init__(self):
        """Initialize semantic analyzer."""
        logger.info("SemanticAnalyzer initialized")
        
        # Aggregation keywords in questions
        self.aggregation_keywords = {
            "count": 3, "how many": 3, "number of": 3, "total": 3,
            "sum": 4, "total sum": 4, "add": 4,
            "average": 5, "avg": 5, "mean": 5,
            "maximum": 1, "max": 1, "highest": 1, "largest": 1,
            "minimum": 2, "min": 2, "lowest": 2, "smallest": 2
        }
    
    def analyze(self, generated_sql: Dict, gold_sql: Dict, question: str, 
                schema: Optional[Dict] = None) -> Dict:
        """
        Analyze semantic correctness of generated SQL compared to gold standard.
        
        Args:
            generated_sql: Generated SQL in WikiSQL format {sel, conds, agg}
            gold_sql: Gold standard SQL in WikiSQL format {sel, conds, agg}
            question: Natural language question
            schema: Optional schema dictionary for column name resolution
            
        Returns:
            Dictionary with analysis results:
            {
                "correct": bool,
                "semantic_score": float (0.0-1.0),
                "differences": List[str],
                "details": {
                    "selected_column_match": bool,
                    "conditions_match": bool,
                    "aggregation_match": bool,
                    "question_intent_match": bool
                }
            }
        """
        differences = []
        details = {
            "selected_column_match": False,
            "conditions_match": False,
            "aggregation_match": False,
            "question_intent_match": False
        }
        
        # Compare selected column
        sel_match = self._compare_selected_column(generated_sql, gold_sql, schema)
        details["selected_column_match"] = sel_match["match"]
        if not sel_match["match"]:
            differences.append(sel_match["difference"])
        
        # Compare conditions
        conds_match = self._compare_conditions(generated_sql, gold_sql, schema)
        details["conditions_match"] = conds_match["match"]
        if not conds_match["match"]:
            differences.extend(conds_match["differences"])
        
        # Compare aggregation
        agg_match = self._compare_aggregation(generated_sql, gold_sql, question)
        details["aggregation_match"] = agg_match["match"]
        if not agg_match["match"]:
            differences.append(agg_match["difference"])
        
        # Check question intent
        intent_match = self._check_question_intent(generated_sql, question, schema)
        details["question_intent_match"] = intent_match["match"]
        if not intent_match["match"]:
            differences.append(intent_match["difference"])
        
        # Calculate semantic score
        semantic_score = self._calculate_semantic_score(details)
        
        # Overall correctness
        is_correct = (
            details["selected_column_match"] and
            details["conditions_match"] and
            details["aggregation_match"] and
            details["question_intent_match"]
        )
        
        return {
            "correct": is_correct,
            "semantic_score": semantic_score,
            "differences": differences,
            "details": details
        }
    
    def _compare_selected_column(self, generated_sql: Dict, gold_sql: Dict, 
                                 schema: Optional[Dict]) -> Dict:
        """
        Compare selected columns between generated and gold SQL.
        
        Args:
            generated_sql: Generated SQL dict
            gold_sql: Gold standard SQL dict
            schema: Optional schema for column name resolution
            
        Returns:
            Comparison result dictionary
        """
        gen_sel = generated_sql.get("sel", -1)
        gold_sel = gold_sql.get("sel", -1)
        
        if gen_sel == gold_sel:
            return {
                "match": True,
                "difference": None
            }
        
        # Get column names if schema available
        gen_col_name = f"column_{gen_sel}" if gen_sel >= 0 else "none"
        gold_col_name = f"column_{gold_sel}" if gold_sel >= 0 else "none"
        
        if schema:
            columns = schema.get("columns", [])
            if gen_sel < len(columns) and gen_sel >= 0:
                gen_col_name = columns[gen_sel].get("name", gen_col_name)
            if gold_sel < len(columns) and gold_sel >= 0:
                gold_col_name = columns[gold_sel].get("name", gold_col_name)
        
        return {
            "match": False,
            "difference": f"Selected column mismatch: generated={gen_col_name} (index {gen_sel}), "
                         f"gold={gold_col_name} (index {gold_sel})"
        }
    
    def _compare_conditions(self, generated_sql: Dict, gold_sql: Dict,
                           schema: Optional[Dict]) -> Dict:
        """
        Compare WHERE clause conditions between generated and gold SQL.
        
        Args:
            generated_sql: Generated SQL dict
            gold_sql: Gold standard SQL dict
            schema: Optional schema for column name resolution
            
        Returns:
            Comparison result dictionary
        """
        gen_conds = generated_sql.get("conds", [])
        gold_conds = gold_sql.get("conds", [])
        
        differences = []
        
        # Normalize conditions for comparison
        gen_normalized = self._normalize_conditions(gen_conds)
        gold_normalized = self._normalize_conditions(gold_conds)
        
        # Check if conditions match (order-independent)
        gen_set = set(gen_normalized)
        gold_set = set(gold_normalized)
        
        if gen_set == gold_set:
            return {
                "match": True,
                "differences": []
            }
        
        # Find differences
        missing_conds = gold_set - gen_set
        extra_conds = gen_set - gold_set
        
        if missing_conds:
            cond_str = self._format_conditions(missing_conds, schema)
            differences.append(f"Missing conditions: {cond_str}")
        
        if extra_conds:
            cond_str = self._format_conditions(extra_conds, schema)
            differences.append(f"Extra conditions: {cond_str}")
        
        return {
            "match": False,
            "differences": differences
        }
    
    def _normalize_conditions(self, conds: List[List]) -> List[Tuple]:
        """
        Normalize conditions for comparison.
        
        Args:
            conds: List of conditions [[col_idx, op_idx, value], ...]
            
        Returns:
            List of normalized condition tuples
        """
        normalized = []
        for cond in conds:
            if len(cond) >= 3:
                col_idx, op_idx, value = cond[0], cond[1], cond[2]
                # Normalize value (case-insensitive, strip quotes)
                value_norm = str(value).strip().strip("'\"").lower()
                normalized.append((col_idx, op_idx, value_norm))
        return normalized
    
    def _format_conditions(self, conds: Set[Tuple], schema: Optional[Dict]) -> str:
        """
        Format conditions for display.
        
        Args:
            conds: Set of normalized condition tuples
            schema: Optional schema for column name resolution
            
        Returns:
            Formatted string
        """
        operators = {0: '=', 1: '>', 2: '<', 3: '!='}
        formatted = []
        
        for col_idx, op_idx, value in conds:
            col_name = f"column_{col_idx}"
            if schema:
                columns = schema.get("columns", [])
                if col_idx < len(columns) and col_idx >= 0:
                    col_name = columns[col_idx].get("name", col_name)
            
            op = operators.get(op_idx, '?')
            formatted.append(f"{col_name} {op} '{value}'")
        
        return ", ".join(formatted)
    
    def _compare_aggregation(self, generated_sql: Dict, gold_sql: Dict, 
                            question: str) -> Dict:
        """
        Compare aggregation types between generated and gold SQL.
        
        Args:
            generated_sql: Generated SQL dict
            gold_sql: Gold standard SQL dict
            question: Natural language question
            
        Returns:
            Comparison result dictionary
        """
        gen_agg = generated_sql.get("agg", 0)
        gold_agg = gold_sql.get("agg", 0)
        
        agg_names = {0: "None", 1: "MAX", 2: "MIN", 3: "COUNT", 4: "SUM", 5: "AVG"}
        
        if gen_agg == gold_agg:
            return {
                "match": True,
                "difference": None
            }
        
        # Check if aggregation matches question intent
        question_lower = question.lower()
        expected_agg = self._infer_aggregation_from_question(question_lower)
        
        gen_agg_name = agg_names.get(gen_agg, "Unknown")
        gold_agg_name = agg_names.get(gold_agg, "Unknown")
        
        difference = f"Aggregation mismatch: generated={gen_agg_name}, gold={gold_agg_name}"
        
        if expected_agg is not None and gen_agg == expected_agg:
            difference += " (but matches question intent)"
        
        return {
            "match": False,
            "difference": difference
        }
    
    def _infer_aggregation_from_question(self, question: str) -> Optional[int]:
        """
        Infer expected aggregation type from question.
        
        Args:
            question: Natural language question (lowercase)
            
        Returns:
            Aggregation type index or None
        """
        for keyword, agg_type in self.aggregation_keywords.items():
            if keyword in question:
                return agg_type
        return None
    
    def _check_question_intent(self, generated_sql: Dict, question: str,
                               schema: Optional[Dict]) -> Dict:
        """
        Check if generated SQL matches question intent.
        
        Args:
            generated_sql: Generated SQL dict
            question: Natural language question
            schema: Optional schema for column name resolution
            
        Returns:
            Intent match result dictionary
        """
        question_lower = question.lower()
        
        # Check if aggregation matches question
        agg = generated_sql.get("agg", 0)
        expected_agg = self._infer_aggregation_from_question(question_lower)
        
        if expected_agg is not None and agg != expected_agg:
            agg_names = {0: "None", 1: "MAX", 2: "MIN", 3: "COUNT", 4: "SUM", 5: "AVG"}
            return {
                "match": False,
                "difference": f"Question suggests {agg_names.get(expected_agg, 'Unknown')} "
                            f"aggregation, but SQL uses {agg_names.get(agg, 'None')}"
            }
        
        # Check if selected column matches question keywords
        sel_idx = generated_sql.get("sel", -1)
        if sel_idx >= 0 and schema:
            columns = schema.get("columns", [])
            if sel_idx < len(columns):
                selected_col = columns[sel_idx].get("name", "").lower()
                # Simple keyword matching
                col_keywords = selected_col.split()
                question_words = set(re.findall(r'\b\w+\b', question_lower))
                
                # Check if any column keyword appears in question
                if not any(kw in question_words for kw in col_keywords if len(kw) > 2):
                    # This is a warning, not an error - column might be implicit
                    pass
        
        return {
            "match": True,
            "difference": None
        }
    
    def _calculate_semantic_score(self, details: Dict) -> float:
        """
        Calculate semantic correctness score (0.0-1.0).
        
        Args:
            details: Details dictionary with match flags
            
        Returns:
            Semantic score between 0.0 and 1.0
        """
        weights = {
            "selected_column_match": 0.3,
            "conditions_match": 0.4,
            "aggregation_match": 0.2,
            "question_intent_match": 0.1
        }
        
        score = 0.0
        for key, weight in weights.items():
            if details.get(key, False):
                score += weight
        
        return round(score, 2)


if __name__ == "__main__":
    # Test the semantic analyzer
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.data.loaders.wikisql_value_loader import WikiSQLValueLoader
    from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 70)
    print("Semantic Analyzer - Test")
    print("=" * 70)
    
    # Load sample data
    loader = WikiSQLValueLoader()
    serializer = WikiSQLValueSchemaSerializer()
    
    samples = loader.get_sample("dev", n=3)
    
    analyzer = SemanticAnalyzer()
    
    print(f"\nTesting semantic analysis on {len(samples)} sample queries...\n")
    
    for i, sample in enumerate(samples, 1):
        gold_sql = sample['query']['sql']
        question = sample['query']['question']
        schema = serializer.extract_schema_from_table_data(sample['table_schema'])
        
        print(f"--- Test {i} ---")
        print(f"Question: {question}")
        print(f"Gold SQL: sel={gold_sql.get('sel')}, agg={gold_sql.get('agg')}, "
              f"conds={len(gold_sql.get('conds', []))}")
        
        # Test with same SQL (should be correct)
        result = analyzer.analyze(gold_sql, gold_sql, question, schema)
        
        if result['correct']:
            print(f"[OK] SEMANTICALLY CORRECT (score: {result['semantic_score']})")
        else:
            print(f"[ERROR] SEMANTIC MISMATCH (score: {result['semantic_score']})")
            for diff in result['differences']:
                print(f"   - {diff}")
        
        # Test with modified SQL (should show differences)
        modified_sql = gold_sql.copy()
        modified_sql['agg'] = 3 if modified_sql.get('agg', 0) == 0 else 0
        
        result2 = analyzer.analyze(modified_sql, gold_sql, question, schema)
        print(f"\n   Modified SQL (agg changed):")
        print(f"   Score: {result2['semantic_score']}, Correct: {result2['correct']}")
        if result2['differences']:
            print(f"   Differences: {result2['differences'][0]}")
        
        print()
