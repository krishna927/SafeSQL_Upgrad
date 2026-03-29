"""Grammar-guided generation for Guardrails Layer.

This module ensures generated SQL follows valid SQL grammar rules.
"""

from typing import List, Dict, Optional, Set
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GrammarGuidedGenerator:
    """Grammar-guided SQL generator."""
    
    def __init__(self):
        """Initialize grammar-guided generator."""
        # SQL keyword patterns
        self.sql_keywords = {
            "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING",
            "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "ON",
            "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MAX", "MIN",
            "AND", "OR", "NOT", "IN", "LIKE", "BETWEEN", "IS NULL"
        }
        
        # Valid SQL structure patterns
        self.valid_patterns = [
            r"SELECT\s+.*\s+FROM\s+\w+",  # Basic SELECT FROM
            r"SELECT\s+.*\s+FROM\s+\w+\s+WHERE\s+.*",  # SELECT FROM WHERE
            r"SELECT\s+(?:COUNT|SUM|AVG|MAX|MIN)\s*\(.*\)\s+FROM\s+\w+",  # Aggregation
        ]
        
        logger.info("GrammarGuidedGenerator initialized")
    
    def validate_sql_structure(self, sql: str) -> Dict:
        """
        Validate SQL structure against grammar rules.
        
        Args:
            sql: SQL query string
            
        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        sql_upper = sql.upper().strip()
        
        # Check 1: Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            errors.append("SQL must start with SELECT")
        
        # Check 2: Must have FROM clause
        if "FROM" not in sql_upper:
            errors.append("SQL must contain FROM clause")
        
        # Check 3: Check for balanced parentheses
        open_parens = sql.count('(')
        close_parens = sql.count(')')
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing")
        
        # Check 4: Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("''")
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes")
        
        # Check 5: Valid keyword sequence
        keyword_sequence = self._extract_keyword_sequence(sql_upper)
        if not self._is_valid_keyword_sequence(keyword_sequence):
            warnings.append("Unusual keyword sequence detected")
        
        # Check 6: Valid aggregation usage
        if self._has_aggregation_without_group_by(sql_upper):
            # This is a warning, not an error (might be intentional)
            warnings.append("Aggregation used without GROUP BY")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _extract_keyword_sequence(self, sql: str) -> List[str]:
        """Extract sequence of SQL keywords."""
        keywords = []
        words = re.findall(r'\b\w+\b', sql.upper())
        
        for word in words:
            if word in self.sql_keywords:
                keywords.append(word)
        
        return keywords
    
    def _is_valid_keyword_sequence(self, sequence: List[str]) -> bool:
        """Check if keyword sequence is valid."""
        if not sequence:
            return False
        
        # Basic validation: SELECT should come first
        if sequence[0] != "SELECT":
            return False
        
        # FROM should appear after SELECT
        if "FROM" not in sequence:
            return False
        
        # WHERE should come after FROM
        if "WHERE" in sequence:
            from_idx = sequence.index("FROM")
            where_idx = sequence.index("WHERE")
            if where_idx < from_idx:
                return False
        
        return True
    
    def _has_aggregation_without_group_by(self, sql: str) -> bool:
        """Check if aggregation is used without GROUP BY."""
        has_aggregation = re.search(r'(COUNT|SUM|AVG|MAX|MIN)\s*\(', sql, re.IGNORECASE)
        has_group_by = re.search(r'GROUP\s+BY', sql, re.IGNORECASE)
        
        return bool(has_aggregation and not has_group_by)
    
    def get_valid_continuations(self, partial_sql: str) -> List[str]:
        """
        Get valid SQL continuations for partial SQL.
        
        Args:
            partial_sql: Partial SQL query
            
        Returns:
            List of valid continuation keywords/patterns
        """
        partial_upper = partial_sql.upper().strip()
        continuations = []
        
        # If starts with SELECT, can continue with column names or aggregations
        if partial_upper.startswith("SELECT"):
            if "FROM" not in partial_upper:
                continuations.extend(["column_name", "COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT"])
            elif "WHERE" not in partial_upper:
                continuations.extend(["WHERE", "GROUP BY", "ORDER BY"])
            else:
                continuations.extend(["AND", "OR", "ORDER BY", "GROUP BY"])
        
        return continuations
