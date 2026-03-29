"""Unit tests for SQL parser."""

import pytest
from src.utils.sql_parser import SQLParser


class TestSQLParser:
    """Test cases for SQLParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SQLParser()
    
    def test_get_operation_type_select(self):
        """Test extracting SELECT operation."""
        sql = "SELECT * FROM users"
        assert self.parser.get_operation_type(sql) == "SELECT"
    
    def test_get_operation_type_delete(self):
        """Test extracting DELETE operation."""
        sql = "DELETE FROM users WHERE id = 1"
        assert self.parser.get_operation_type(sql) == "DELETE"
    
    def test_has_where_clause(self):
        """Test WHERE clause detection."""
        sql_with_where = "SELECT * FROM users WHERE id = 1"
        sql_without_where = "SELECT * FROM users"
        
        assert self.parser.has_where_clause(sql_with_where) is True
        assert self.parser.has_where_clause(sql_without_where) is False
    
    def test_is_destructive_operation_drop(self):
        """Test detection of DROP operations."""
        sql = "DROP TABLE users"
        assert self.parser.is_destructive_operation(sql) is True
    
    def test_is_destructive_operation_delete_without_where(self):
        """Test detection of DELETE without WHERE."""
        sql = "DELETE FROM users"
        assert self.parser.is_destructive_operation(sql) is True
    
    def test_is_destructive_operation_delete_with_where(self):
        """Test that DELETE with WHERE is not destructive."""
        sql = "DELETE FROM users WHERE id = 1"
        assert self.parser.is_destructive_operation(sql) is False
    
    def test_get_tables(self):
        """Test table name extraction."""
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        tables = self.parser.get_tables(sql)
        assert "users" in tables
        assert "orders" in tables
    
    def test_validate_syntax_valid(self):
        """Test syntax validation for valid SQL."""
        sql = "SELECT * FROM users WHERE id = 1"
        is_valid, error = self.parser.validate_syntax(sql)
        assert is_valid is True
        assert error is None
    
    def test_validate_syntax_invalid(self):
        """Test syntax validation for invalid SQL."""
        sql = "SELECT * FROM users WHERE (id = 1"  # Unbalanced parentheses
        is_valid, error = self.parser.validate_syntax(sql)
        assert is_valid is False
        assert error is not None
