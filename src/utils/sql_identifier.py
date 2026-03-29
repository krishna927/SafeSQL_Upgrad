"""SQL identifier quoting utilities.

This module provides functions to properly quote SQL identifiers (table names,
column names) that contain special characters, ensuring valid SQL syntax.
"""

import re
from typing import Optional


def needs_quoting(identifier: str) -> bool:
    """
    Check if an identifier needs quoting.
    
    SQL identifiers need quoting if they:
    - Contain spaces
    - Contain special characters (/, -, ., etc.)
    - Are SQL keywords (when used as identifiers)
    - Start with a number
    
    Args:
        identifier: Identifier name
        
    Returns:
        True if identifier needs quoting
    """
    if not identifier:
        return False
    
    # Remove existing quotes
    identifier = identifier.strip().strip('"').strip("'")
    
    # Check if it's already quoted
    if (identifier.startswith('"') and identifier.endswith('"')) or \
       (identifier.startswith("'") and identifier.endswith("'")):
        return False
    
    # SQLite identifiers need quoting if they:
    # 1. Contain spaces
    if ' ' in identifier:
        return True
    
    # 2. Contain special characters (/, -, ., etc.) except underscore
    if re.search(r'[^a-zA-Z0-9_]', identifier):
        return True
    
    # 3. Start with a number
    if identifier[0].isdigit():
        return True
    
    # 4. Are SQL keywords (basic check)
    sql_keywords = {
        'select', 'from', 'where', 'group', 'order', 'by', 'having',
        'join', 'inner', 'left', 'right', 'outer', 'on', 'as', 'and', 'or',
        'not', 'in', 'like', 'between', 'is', 'null', 'exists', 'case',
        'when', 'then', 'else', 'end', 'union', 'intersect', 'except',
        'distinct', 'all', 'limit', 'offset', 'insert', 'update', 'delete',
        'create', 'drop', 'alter', 'table', 'index', 'view', 'database',
        'schema', 'column', 'constraint', 'primary', 'key', 'foreign',
        'references', 'check', 'default', 'not', 'null', 'unique'
    }
    if identifier.lower() in sql_keywords:
        return True
    
    return False


def quote_identifier(identifier: str, force: bool = False) -> str:
    """
    Quote an SQL identifier if needed.
    
    Uses double quotes for SQLite compatibility. Escapes any double quotes
    within the identifier.
    
    Args:
        identifier: Identifier name
        force: Force quoting even if not needed
        
    Returns:
        Quoted identifier string
    """
    if not identifier:
        return '""'
    
    # Remove existing quotes
    identifier = identifier.strip().strip('"').strip("'")
    
    # Escape double quotes within identifier
    identifier = identifier.replace('"', '""')
    
    # Quote if needed or forced
    if force or needs_quoting(identifier):
        return f'"{identifier}"'
    
    return identifier


def unquote_identifier(identifier: str) -> str:
    """
    Remove quotes from an identifier.
    
    Args:
        identifier: Possibly quoted identifier
        
    Returns:
        Unquoted identifier
    """
    if not identifier:
        return ""
    
    identifier = identifier.strip()
    
    # Remove double quotes
    if identifier.startswith('"') and identifier.endswith('"'):
        identifier = identifier[1:-1]
        # Unescape double quotes
        identifier = identifier.replace('""', '"')
    
    # Remove single quotes (less common for identifiers)
    if identifier.startswith("'") and identifier.endswith("'"):
        identifier = identifier[1:-1]
        # Unescape single quotes
        identifier = identifier.replace("''", "'")
    
    return identifier


def quote_column_name(column_name: str) -> str:
    """
    Quote a column name if it contains special characters.
    
    Convenience function for column names.
    
    Args:
        column_name: Column name
        
    Returns:
        Quoted column name
    """
    return quote_identifier(column_name)


def quote_table_name(table_name: str) -> str:
    """
    Quote a table name if it contains special characters.
    
    Convenience function for table names.
    
    Args:
        table_name: Table name
        
    Returns:
        Quoted table name
    """
    return quote_identifier(table_name)


def extract_quoted_identifier(sql: str, start_pos: int = 0) -> Optional[tuple]:
    """
    Extract a quoted identifier from SQL string.
    
    Args:
        sql: SQL string
        start_pos: Starting position to search from
        
    Returns:
        Tuple of (identifier, end_position) or None if not found
    """
    sql = sql[start_pos:]
    
    # Look for double-quoted identifier
    if sql.startswith('"'):
        end_pos = sql.find('"', 1)
        if end_pos == -1:
            return None
        
        # Handle escaped quotes
        while end_pos < len(sql) - 1 and sql[end_pos + 1] == '"':
            end_pos = sql.find('"', end_pos + 2)
            if end_pos == -1:
                return None
        
        identifier = sql[1:end_pos].replace('""', '"')
        return (identifier, start_pos + end_pos + 1)
    
    return None


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "School/Club Team",
        "No.",
        "table_name",
        "normal_column",
        "Column With Spaces",
        "column-name",
        "column.name",
        "123column",
        "SELECT",  # SQL keyword
    ]
    
    print("Testing identifier quoting:")
    for test in test_cases:
        quoted = quote_identifier(test)
        unquoted = unquote_identifier(quoted)
        needs = needs_quoting(test)
        print(f"  '{test}' -> '{quoted}' (needs quoting: {needs}, round-trip: {test == unquoted})")
