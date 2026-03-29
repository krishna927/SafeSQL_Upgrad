"""Guardrails Layer Orchestrator.

This module coordinates all guardrails components to prevent unsafe SQL
operations during generation.
"""

from typing import Dict, Optional, List
import re

from .token_filter import TokenFilter
from .pattern_matcher import PatternMatcher
from .constrained_decoding import ConstrainedDecoder
from .grammar_guided import GrammarGuidedGenerator
from .policy_enforcer import PolicyEnforcer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Guardrails:
    """Main guardrails orchestrator."""
    
    def __init__(self, policy_file: Optional[str] = None):
        """
        Initialize guardrails.
        
        Args:
            policy_file: Path to safety policy file
        """
        self.token_filter = TokenFilter()
        self.pattern_matcher = PatternMatcher()
        self.constrained_decoder = ConstrainedDecoder()
        self.grammar_guided = GrammarGuidedGenerator()
        self.policy_enforcer = PolicyEnforcer(policy_file)
        
        logger.info("Guardrails initialized")
    
    def apply_guardrails(self, sql: str) -> Dict:
        """
        Apply all guardrails to SQL query.
        
        Args:
            sql: Generated SQL query
            
        Returns:
            Dictionary with guardrails results:
            {
                "safe": bool,
                "allowed": bool,
                "violations": List[str],
                "checks": {
                    "token_filter": Dict,
                    "pattern_match": Dict,
                    "constraints": Dict,
                    "grammar": Dict,
                    "policies": Dict
                }
            }
        """
        violations = []
        checks = {}
        
        # Check 1: Token Filter
        token_result = self.token_filter.filter_sql(sql)
        checks["token_filter"] = token_result
        if not token_result["safe"]:
            violations.extend(token_result["violations"])
        
        # Check 2: Pattern Matcher
        patterns = self.pattern_matcher.detect_patterns(sql)
        checks["pattern_match"] = {
            "patterns_found": len(patterns),
            "patterns": patterns,
            "has_critical": self.pattern_matcher.has_critical_violations(sql)
        }
        if patterns:
            violations.extend([p["description"] for p in patterns])
        
        # Check 3: Constrained Decoding
        constraint_result = self.constrained_decoder.check_constraints(sql)
        checks["constraints"] = constraint_result
        if constraint_result["violates_constraints"]:
            violations.extend(constraint_result["violations"])
        
        # Check 4: Grammar Validation
        grammar_result = self.grammar_guided.validate_sql_structure(sql)
        checks["grammar"] = grammar_result
        if not grammar_result["valid"]:
            violations.extend(grammar_result["errors"])
        
        # Check 5: Policy Enforcement
        policy_result = self.policy_enforcer.enforce_policies(sql)
        checks["policies"] = policy_result
        if not policy_result["compliant"]:
            violations.extend(policy_result["violations"])
        
        # Overall safety decision
        is_safe = (
            token_result["safe"] and
            len(patterns) == 0 and
            not constraint_result["violates_constraints"] and
            grammar_result["valid"] and
            policy_result["compliant"]
        )
        
        return {
            "safe": is_safe,
            "allowed": is_safe,
            "violations": list(set(violations)),  # Remove duplicates
            "checks": checks
        }
    
    def build_safe_prompt(self, base_prompt: str, schema: Optional[Dict] = None) -> str:
        """
        Build prompt with safety constraints.
        
        Args:
            base_prompt: Base prompt
            schema: Database schema
            
        Returns:
            Prompt with safety constraints added
        """
        return self.constrained_decoder.build_constrained_prompt(base_prompt, schema)
    
    def filter_and_validate(self, sql: str) -> Dict:
        """
        Filter and validate SQL query.
        
        Args:
            sql: Generated SQL query
            
        Returns:
            Filtering and validation results
        """
        return self.apply_guardrails(sql)
