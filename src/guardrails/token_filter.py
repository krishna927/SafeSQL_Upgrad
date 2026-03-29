"""Token filtering for Guardrails Layer.

This module filters dangerous tokens and patterns from generated SQL.
Since OpenAI API doesn't provide token-level access, we filter the
complete generated SQL string.
"""

from typing import List, Set, Dict, Optional
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TokenFilter:
    """Filters dangerous tokens and patterns from SQL."""
    
    def __init__(self, forbidden_operations: Optional[List[str]] = None):
        """
        Initialize token filter.
        
        Args:
            forbidden_operations: List of forbidden SQL operations
        """
        # Default forbidden operations
        self.forbidden_operations = forbidden_operations or [
            "DROP", "TRUNCATE", "ALTER", "CREATE", "INSERT", 
            "UPDATE", "DELETE", "GRANT", "REVOKE"
        ]
        
        # Forbidden patterns (more specific)
        self.forbidden_patterns = [
            r"DROP\s+TABLE",
            r"DROP\s+DATABASE",
            r"TRUNCATE\s+TABLE",
            r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",  # DELETE without WHERE
            r"UPDATE\s+\w+\s+SET\s+(?!WHERE)",  # UPDATE without WHERE
            r"ALTER\s+TABLE",
            r"CREATE\s+TABLE",
            r"INSERT\s+INTO",
        ]
        
        logger.info(f"TokenFilter initialized with {len(self.forbidden_operations)} forbidden operations")
    
    def filter_sql(self, sql: str) -> Dict:
        """
        Filter SQL for dangerous operations.
        
        Args:
            sql: SQL query string
            
        Returns:
            Dictionary with filtering results:
            {
                "safe": bool,
                "filtered_sql": str,
                "violations": List[str],
                "blocked_operations": List[str]
            }
        """
        violations = []
        blocked_operations = []
        filtered_sql = sql
        
        sql_upper = sql.upper()
        
        # Check for forbidden operations
        for op in self.forbidden_operations:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(op.upper()) + r'\b'
            if re.search(pattern, sql_upper):
                violations.append(f"Forbidden operation detected: {op}")
                blocked_operations.append(op)
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            matches = re.finditer(pattern, sql_upper, re.IGNORECASE)
            for match in matches:
                violation = f"Forbidden pattern detected: {match.group(0)}"
                if violation not in violations:
                    violations.append(violation)
        
        # Special check: DELETE/UPDATE without WHERE
        if self._has_dangerous_delete_or_update(sql):
            violations.append("DELETE or UPDATE without WHERE clause detected")
        
        # If violations found, mark as unsafe
        is_safe = len(violations) == 0
        
        return {
            "safe": is_safe,
            "filtered_sql": filtered_sql,  # Return original (filtering happens at generation)
            "violations": violations,
            "blocked_operations": blocked_operations
        }
    
    def _has_dangerous_delete_or_update(self, sql: str) -> bool:
        """
        Check if SQL has DELETE or UPDATE without WHERE clause.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if dangerous DELETE/UPDATE detected
        """
        sql_upper = sql.upper().strip()
        
        # Check for DELETE without WHERE
        delete_match = re.search(r'DELETE\s+FROM\s+(\w+)', sql_upper)
        if delete_match:
            # Check if WHERE follows
            after_delete = sql_upper[delete_match.end():].strip()
            if not after_delete.startswith("WHERE"):
                return True
        
        # Check for UPDATE without WHERE
        update_match = re.search(r'UPDATE\s+(\w+)\s+SET\s+[^W]+(?!WHERE)', sql_upper)
        if update_match:
            # More careful check
            update_part = sql_upper[:update_match.end()]
            if "WHERE" not in sql_upper[update_match.end():]:
                return True
        
        return False
    
    def is_token_safe(self, token: str, context: str = "") -> bool:
        """
        Check if a token is safe given context.
        
        Args:
            token: Token to check
            context: Current SQL context
            
        Returns:
            True if token is safe
        """
        token_upper = token.upper().strip()
        
        # Check if token is a forbidden operation
        if token_upper in [op.upper() for op in self.forbidden_operations]:
            return False
        
        # Check context for dangerous patterns
        context_upper = context.upper()
        
        # Allow DELETE/UPDATE only if WHERE is present or coming
        if token_upper in ["DELETE", "UPDATE"]:
            if "WHERE" not in context_upper:
                # Check if WHERE might come after
                # This is a simplified check - in practice would need more context
                return False
        
        return True
    
    def get_allowed_operations(self) -> List[str]:
        """
        Get list of allowed SQL operations.
        
        Returns:
            List of allowed operations
        """
        # Only SELECT is allowed for read-only queries
        return ["SELECT"]
    
    def get_forbidden_operations(self) -> List[str]:
        """
        Get list of forbidden SQL operations.
        
        Returns:
            List of forbidden operations
        """
        return self.forbidden_operations.copy()
