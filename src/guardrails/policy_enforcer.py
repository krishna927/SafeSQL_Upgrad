"""Safety policy enforcement for Guardrails Layer.

This module enforces organizational safety policies on SQL generation.
"""

from typing import Dict, List, Optional
import re
import yaml
from pathlib import Path

from .token_filter import TokenFilter
from .pattern_matcher import PatternMatcher
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PolicyEnforcer:
    """Enforces safety policies on SQL generation."""
    
    def __init__(self, policy_file: Optional[str] = None):
        """
        Initialize policy enforcer.
        
        Args:
            policy_file: Path to policy YAML file
        """
        self.policies = self._load_policies(policy_file)
        self.token_filter = TokenFilter(
            forbidden_operations=self.policies.get("forbidden_operations", [])
        )
        self.pattern_matcher = PatternMatcher()
        
        logger.info(f"PolicyEnforcer initialized with {len(self.policies)} policy rules")
    
    def _load_policies(self, policy_file: Optional[str]) -> Dict:
        """
        Load policies from file or use defaults.
        
        Args:
            policy_file: Path to policy file
            
        Returns:
            Policy dictionary
        """
        if policy_file and Path(policy_file).exists():
            try:
                with open(policy_file, 'r') as f:
                    policies = yaml.safe_load(f)
                    return policies or {}
            except Exception as e:
                logger.warning(f"Failed to load policy file: {e}. Using defaults.")
        
        # Default policies
        return {
            "forbidden_operations": [
                "DROP", "TRUNCATE", "ALTER", "CREATE", 
                "INSERT", "UPDATE", "DELETE", "GRANT", "REVOKE"
            ],
            "require_where_for_delete": True,
            "require_where_for_update": True,
            "allowed_operations": ["SELECT"],
            "max_query_complexity": 100,
            "block_destructive_operations": True
        }
    
    def enforce_policies(self, sql: str) -> Dict:
        """
        Enforce all safety policies on SQL.
        
        Args:
            sql: SQL query string
            
        Returns:
            Dictionary with enforcement results:
            {
                "compliant": bool,
                "violations": List[str],
                "policy_checks": Dict
            }
        """
        violations = []
        policy_checks = {}
        
        # Check 1: Allowed operations only
        if self.policies.get("allowed_operations"):
            allowed = self.policies["allowed_operations"]
            sql_upper = sql.upper()
            for op in ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "TRUNCATE"]:
                if op in sql_upper and op not in allowed:
                    violations.append(f"Operation '{op}' not in allowed operations: {allowed}")
        
        policy_checks["allowed_operations"] = len(violations) == 0
        
        # Check 2: Require WHERE for DELETE
        if self.policies.get("require_where_for_delete", True):
            if "DELETE" in sql.upper() and "WHERE" not in sql.upper():
                violations.append("DELETE operation requires WHERE clause")
        
        policy_checks["delete_requires_where"] = "DELETE" not in sql.upper() or "WHERE" in sql.upper()
        
        # Check 3: Require WHERE for UPDATE
        if self.policies.get("require_where_for_update", True):
            if "UPDATE" in sql.upper():
                # Check if WHERE appears after SET
                update_match = re.search(r'UPDATE\s+\w+\s+SET', sql.upper())
                if update_match:
                    after_set = sql[update_match.end():].upper()
                    if "WHERE" not in after_set:
                        violations.append("UPDATE operation requires WHERE clause")
        
        policy_checks["update_requires_where"] = "UPDATE" not in sql.upper() or "WHERE" in sql.upper()
        
        # Check 4: Block destructive operations
        if self.policies.get("block_destructive_operations", True):
            patterns = self.pattern_matcher.detect_patterns(sql)
            critical_patterns = [p for p in patterns if p["severity"] == "CRITICAL"]
            if critical_patterns:
                violations.append(f"Destructive operations blocked: {[p['description'] for p in critical_patterns]}")
        
        policy_checks["no_destructive_operations"] = len([p for p in self.pattern_matcher.detect_patterns(sql) if p["severity"] == "CRITICAL"]) == 0
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "policy_checks": policy_checks
        }
    
    def check_access_control(self, sql: str, user_permissions: Optional[Dict] = None) -> Dict:
        """
        Check access control policies.
        
        Args:
            sql: SQL query string
            user_permissions: User permissions dictionary
            
        Returns:
            Access control check results
        """
        # Placeholder for access control
        # In production, would check user permissions against tables/columns
        return {
            "allowed": True,
            "reason": "Access control not implemented"
        }
