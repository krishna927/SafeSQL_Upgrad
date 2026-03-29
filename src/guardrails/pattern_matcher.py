"""Pattern matching for detecting unsafe SQL patterns.

This module detects dangerous SQL patterns using regex and pattern matching.
"""

from typing import List, Dict, Tuple
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PatternMatcher:
    """Matches dangerous SQL patterns."""
    
    def __init__(self):
        """Initialize pattern matcher."""
        # Dangerous patterns with descriptions
        self.dangerous_patterns = [
            {
                "pattern": r"DROP\s+TABLE\s+\w+",
                "description": "DROP TABLE operation",
                "severity": "CRITICAL"
            },
            {
                "pattern": r"DROP\s+DATABASE\s+\w+",
                "description": "DROP DATABASE operation",
                "severity": "CRITICAL"
            },
            {
                "pattern": r"TRUNCATE\s+TABLE\s+\w+",
                "description": "TRUNCATE TABLE operation",
                "severity": "CRITICAL"
            },
            {
                "pattern": r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",
                "description": "DELETE without WHERE clause",
                "severity": "HIGH"
            },
            {
                "pattern": r"UPDATE\s+\w+\s+SET\s+[^W]*(?!WHERE)",
                "description": "UPDATE without WHERE clause",
                "severity": "HIGH"
            },
            {
                "pattern": r"ALTER\s+TABLE\s+\w+",
                "description": "ALTER TABLE operation",
                "severity": "HIGH"
            },
            {
                "pattern": r"CREATE\s+TABLE\s+\w+",
                "description": "CREATE TABLE operation",
                "severity": "MEDIUM"
            },
            {
                "pattern": r"INSERT\s+INTO\s+\w+",
                "description": "INSERT operation",
                "severity": "MEDIUM"
            },
            {
                "pattern": r"GRANT\s+.*\s+TO\s+",
                "description": "GRANT operation",
                "severity": "HIGH"
            },
            {
                "pattern": r"REVOKE\s+.*\s+FROM\s+",
                "description": "REVOKE operation",
                "severity": "HIGH"
            }
        ]
        
        logger.info(f"PatternMatcher initialized with {len(self.dangerous_patterns)} patterns")
    
    def detect_patterns(self, sql: str) -> List[Dict]:
        """
        Detect dangerous patterns in SQL.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of detected patterns with details:
            [{
                "pattern": str,
                "description": str,
                "severity": str,
                "match": str,
                "position": int
            }]
        """
        detected = []
        sql_upper = sql.upper()
        
        for pattern_info in self.dangerous_patterns:
            pattern = pattern_info["pattern"]
            matches = re.finditer(pattern, sql_upper, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                detected.append({
                    "pattern": pattern,
                    "description": pattern_info["description"],
                    "severity": pattern_info["severity"],
                    "match": match.group(0),
                    "position": match.start()
                })
        
        return detected
    
    def has_critical_violations(self, sql: str) -> bool:
        """
        Check if SQL has critical violations.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if critical violations found
        """
        patterns = self.detect_patterns(sql)
        return any(p["severity"] == "CRITICAL" for p in patterns)
    
    def has_high_severity_violations(self, sql: str) -> bool:
        """
        Check if SQL has high or critical severity violations.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if high/critical violations found
        """
        patterns = self.detect_patterns(sql)
        return any(p["severity"] in ["CRITICAL", "HIGH"] for p in patterns)
    
    def is_safe(self, sql: str) -> Tuple[bool, List[Dict]]:
        """
        Check if SQL is safe.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple of (is_safe, detected_patterns)
        """
        patterns = self.detect_patterns(sql)
        is_safe = len(patterns) == 0
        
        return is_safe, patterns
