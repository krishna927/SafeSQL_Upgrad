"""Database connection and management utilities."""

import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import psycopg2
from psycopg2 import pool
import pymysql
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(
        self,
        db_type: str = "sqlite",
        connection_string: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize database manager.
        
        Args:
            db_type: Type of database ('sqlite', 'postgresql', 'mysql')
            connection_string: SQLAlchemy connection string
            **kwargs: Additional connection parameters
        """
        self.db_type = db_type.lower()
        self.connection_string = connection_string
        self.engine: Optional[Engine] = None
        self.inspector: Optional[Any] = None
        self._connection_pool: Optional[Any] = None
        
        # Initialize connection
        self._initialize_connection(**kwargs)
    
    def _initialize_connection(self, **kwargs) -> None:
        """Initialize database connection based on type."""
        if self.db_type == "sqlite":
            db_path = kwargs.get("db_path", "data/datasets/databases")
            if not self.connection_string:
                self.connection_string = f"sqlite:///{db_path}"
        elif self.db_type == "postgresql":
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 5432)
            database = kwargs.get("database", "spider")
            user = kwargs.get("user", "postgres")
            password = kwargs.get("password", "")
            if not self.connection_string:
                self.connection_string = (
                    f"postgresql://{user}:{password}@{host}:{port}/{database}"
                )
        elif self.db_type == "mysql":
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 3306)
            database = kwargs.get("database", "spider")
            user = kwargs.get("user", "root")
            password = kwargs.get("password", "")
            if not self.connection_string:
                self.connection_string = (
                    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
                )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        
        try:
            self.engine = create_engine(self.connection_string, echo=False)
            self.inspector = inspect(self.engine)
            logger.info(f"Connected to {self.db_type} database")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def execute_query(self, query: str, fetch: bool = True) -> Optional[List[Tuple]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            fetch: Whether to fetch results
            
        Returns:
            Query results as list of tuples, or None if fetch=False
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                if fetch:
                    return result.fetchall()
                return None
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def get_schema(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get database schema information.
        
        Args:
            database_name: Name of database (for multi-database systems)
            
        Returns:
            Dictionary containing schema information
        """
        if self.inspector is None:
            raise RuntimeError("Database inspector not initialized")
        
        schema = {
            "tables": {},
            "foreign_keys": [],
            "constraints": {}
        }
        
        try:
            # Get all table names
            table_names = self.inspector.get_table_names(schema=database_name)
            
            for table_name in table_names:
                # Get columns
                columns = self.inspector.get_columns(table_name, schema=database_name)
                
                # Get primary keys
                pk_constraint = self.inspector.get_pk_constraint(table_name, schema=database_name)
                
                # Get foreign keys
                foreign_keys = self.inspector.get_foreign_keys(table_name, schema=database_name)
                
                # Get indexes
                indexes = self.inspector.get_indexes(table_name, schema=database_name)
                
                schema["tables"][table_name] = {
                    "columns": {col["name"]: {
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default"),
                    } for col in columns},
                    "primary_key": pk_constraint.get("constrained_columns", []),
                    "indexes": [idx["name"] for idx in indexes],
                }
                
                schema["foreign_keys"].extend(foreign_keys)
            
            return schema
        except SQLAlchemyError as e:
            logger.error(f"Failed to get schema: {e}")
            raise
    
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists."""
        if self.inspector is None:
            return False
        return self.inspector.has_table(table_name, schema=schema)
    
    def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Check if a column exists in a table."""
        if not self.table_exists(table_name, schema):
            return False
        
        columns = self.inspector.get_columns(table_name, schema=schema)
        return any(col["name"] == column_name for col in columns)
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
