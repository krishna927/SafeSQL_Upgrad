"""Policy-aware constrained decoding for Guardrails Layer.

This module implements constrained decoding to prevent unsafe SQL operations.
Since OpenAI API doesn't provide token-level access, we use post-generation
filtering and regeneration with constraints.
"""

from typing import Dict, List, Optional, Set
import re

from .token_filter import TokenFilter
from .pattern_matcher import PatternMatcher
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConstrainedDecoder:
    """Policy-aware constrained decoder for SQL generation."""
    
    def __init__(self, safety_policies: Optional[Dict] = None):
        """
        Initialize constrained decoder.
        
        Args:
            safety_policies: Safety policy dictionary
        """
        self.safety_policies = safety_policies or {}
        self.token_filter = TokenFilter(
            forbidden_operations=self.safety_policies.get("forbidden_operations")
        )
        self.pattern_matcher = PatternMatcher()
        
        logger.info("ConstrainedDecoder initialized")
    
    def check_constraints(self, sql: str) -> Dict:
        """
        Check if SQL violates constraints.
        
        Args:
            sql: Generated SQL query
            
        Returns:
            Dictionary with constraint check results:
            {
                "violates_constraints": bool,
                "violations": List[str],
                "safe": bool
            }
        """
        violations = []
        
        # Check token filter
        filter_result = self.token_filter.filter_sql(sql)
        if not filter_result["safe"]:
            violations.extend(filter_result["violations"])
        
        # Check pattern matcher
        patterns = self.pattern_matcher.detect_patterns(sql)
        if patterns:
            for pattern in patterns:
                violations.append(
                    f"{pattern['severity']}: {pattern['description']} - {pattern['match']}"
                )
        
        violates_constraints = len(violations) > 0
        
        return {
            "violates_constraints": violates_constraints,
            "violations": violations,
            "safe": not violates_constraints,
            "blocked_operations": filter_result.get("blocked_operations", [])
        }
    
    def enforce_constraints(self, sql: str) -> Dict:
        """
        Enforce constraints on SQL (reject if unsafe).
        
        Args:
            sql: Generated SQL query
            
        Returns:
            Dictionary with enforcement results:
            {
                "allowed": bool,
                "reason": str,
                "violations": List[str]
            }
        """
        constraint_result = self.check_constraints(sql)
        
        if constraint_result["violates_constraints"]:
            return {
                "allowed": False,
                "reason": "SQL violates safety constraints",
                "violations": constraint_result["violations"]
            }
        
        return {
            "allowed": True,
            "reason": "SQL passes all safety constraints",
            "violations": []
        }
    
    def build_constrained_prompt(self, base_prompt: str, schema: Optional[Dict] = None) -> str:
        """
        Build prompt with safety constraints.
        
        Args:
            base_prompt: Base prompt
            schema: Database schema
            
        Returns:
            Constrained prompt with safety instructions
        """
        constraints = [
            "IMPORTANT SAFETY RULES:",
            "1. Generate ONLY SELECT queries (read-only)",
            "2. NEVER generate: DROP, DELETE, TRUNCATE, ALTER, CREATE, INSERT, UPDATE",
            "3. NEVER generate DELETE or UPDATE without WHERE clause",
            "4. Only generate safe, read-only SQL queries"
        ]
        
        constrained_prompt = base_prompt + "\n\n" + "\n".join(constraints)
        
        return constrained_prompt
    
    def filter_generation_result(self, sql: str, max_retries: int = 3) -> Dict:
        """
        Filter generation result and reject if unsafe.
        
        Args:
            sql: Generated SQL query
            max_retries: Maximum retries if unsafe
            
        Returns:
            Dictionary with filtering results:
            {
                "safe": bool,
                "sql": str,
                "violations": List[str],
                "retries": int
            }
        """
        retries = 0
        current_sql = sql
        
        while retries < max_retries:
            constraint_result = self.check_constraints(current_sql)
            
            if constraint_result["safe"]:
                return {
                    "safe": True,
                    "sql": current_sql,
                    "violations": [],
                    "retries": retries
                }
            
            # SQL is unsafe - reject it
            logger.warning(f"Unsafe SQL detected (attempt {retries + 1}): {constraint_result['violations']}")
            retries += 1
        
        # After max retries, still unsafe
        return {
            "safe": False,
            "sql": current_sql,
            "violations": constraint_result["violations"],
            "retries": retries
        }
