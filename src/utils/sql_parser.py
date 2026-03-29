"""SQL parsing and analysis utilities."""

import sqlparse
from sqlparse.sql import Statement, TokenList
from sqlparse.tokens import Keyword, DML, DDL
from typing import List, Dict, Optional, Set
import re

from .logger import get_logger

logger = get_logger(__name__)


class SQLParser:
    """Parser for SQL queries with safety and structure analysis."""
    
    def __init__(self):
        """Initialize SQL parser."""
        self.forbidden_keywords = {
            "DROP", "TRUNCATE", "DROP TABLE", "DROP DATABASE",
            "DROP SCHEMA", "DROP INDEX", "DROP VIEW"
        }
    
    def parse(self, sql: str) -> List[Statement]:
        """
        Parse SQL query into statements.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of parsed SQL statements
        """
        try:
            statements = sqlparse.parse(sql)
            return statements
        except Exception as e:
            logger.error(f"Failed to parse SQL: {e}")
            raise
    
    def get_operation_type(self, sql: str) -> Optional[str]:
        """
        Extract the main operation type (SELECT, INSERT, UPDATE, DELETE, etc.).
        
        Args:
            sql: SQL query string
            
        Returns:
            Operation type or None
        """
        statements = self.parse(sql)
        if not statements:
            return None
        
        first_statement = statements[0]
        for token in first_statement.tokens:
            if token.ttype in (DML, DDL):
                return token.value.upper().strip()
            elif token.ttype is Keyword and token.value.upper() in [
                "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE"
            ]:
                return token.value.upper().strip()
        
        return None
    
    def has_where_clause(self, sql: str) -> bool:
        """
        Check if SQL query has a WHERE clause.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if WHERE clause exists, False otherwise
        """
        sql_upper = sql.upper()
        return "WHERE" in sql_upper
    
    def is_destructive_operation(self, sql: str) -> bool:
        """
        Check if SQL query is a destructive operation.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if destructive, False otherwise
        """
        operation = self.get_operation_type(sql)
        if operation is None:
            return False
        
        # Check for forbidden operations
        if operation in ["DROP", "TRUNCATE"]:
            return True
        
        # Check for DELETE/UPDATE without WHERE
        if operation in ["DELETE", "UPDATE"]:
            if not self.has_where_clause(sql):
                return True
        
        return False
    
    def get_tables(self, sql: str) -> Set[str]:
        """
        Extract table names from SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            Set of table names
        """
        tables = set()
        statements = self.parse(sql)
        
        for statement in statements:
            # Simple regex-based extraction (can be improved)
            # Match FROM, JOIN, UPDATE, INSERT INTO patterns
            patterns = [
                r'FROM\s+(\w+)',
                r'JOIN\s+(\w+)',
                r'UPDATE\s+(\w+)',
                r'INSERT\s+INTO\s+(\w+)',
            ]
            
            sql_upper = sql.upper()
            for pattern in patterns:
                matches = re.findall(pattern, sql_upper, re.IGNORECASE)
                tables.update(matches)
        
        return tables
    
    def get_columns(self, sql: str) -> Set[str]:
        """
        Extract column names from SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            Set of column names
        """
        columns = set()
        statements = self.parse(sql)
        
        for statement in statements:
            # Extract columns from SELECT clause
            select_pattern = r'SELECT\s+(.*?)\s+FROM'
            select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
            
            if select_match:
                select_clause = select_match.group(1)
                # Handle aggregation functions: COUNT(col), SUM(col), etc.
                # Extract column names from function calls
                func_pattern = r'(?:COUNT|SUM|AVG|MAX|MIN)\s*\(\s*([^)]+)\s*\)'
                func_matches = re.findall(func_pattern, select_clause, re.IGNORECASE)
                for col in func_matches:
                    # Remove quotes and clean
                    col_clean = col.strip().strip("'\"")
                    columns.add(col_clean)
                
                # Extract non-function columns
                # Remove function calls first
                select_no_funcs = re.sub(r'(?:COUNT|SUM|AVG|MAX|MIN)\s*\([^)]+\)', '', select_clause, flags=re.IGNORECASE)
                # Split by comma
                for col_part in select_no_funcs.split(','):
                    col = col_part.strip()
                    if col and not col.upper() in ['DISTINCT', 'ALL']:
                        # Remove aliases (AS alias)
                        col = re.sub(r'\s+AS\s+\w+', '', col, flags=re.IGNORECASE).strip()
                        columns.add(col)
            
            # Extract columns from WHERE clause
            where_pattern = r'WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|$)'
            where_match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)
                # Split by AND/OR to get individual conditions
                conditions = re.split(r'\s+(?:AND|OR)\s+', where_clause, flags=re.IGNORECASE)
                for condition in conditions:
                    # Pattern: column operator value
                    # Match column name before operator
                    condition_match = re.match(r'([\w\s/]+?)\s*([<>=!]+)', condition.strip(), re.IGNORECASE)
                    if condition_match:
                        col = condition_match.group(1).strip()
                        # Remove any trailing spaces or invalid characters
                        col_clean = col.strip()
                        if col_clean and not col_clean.upper() in ['AND', 'OR', 'NOT']:
                            columns.add(col_clean)
        
        return columns
    
    def validate_syntax(self, sql: str) -> tuple[bool, Optional[str]]:
        """
        Basic syntax validation.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            statements = self.parse(sql)
            if not statements:
                return False, "No valid SQL statements found"
            
            # Check for balanced parentheses
            if sql.count('(') != sql.count(')'):
                return False, "Unbalanced parentheses"
            
            # Check for balanced quotes
            single_quotes = sql.count("'") - sql.count("\\'")
            if single_quotes % 2 != 0:
                return False, "Unbalanced single quotes"
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def normalize_query(self, sql: str) -> str:
        """
        Normalize SQL query (formatting, case, etc.).
        
        Args:
            sql: SQL query string
            
        Returns:
            Normalized SQL query
        """
        try:
            formatted = sqlparse.format(sql, reindent=True, keyword_case='upper')
            return formatted.strip()
        except Exception as e:
            logger.warning(f"Failed to normalize query: {e}")
            return sql.strip()
