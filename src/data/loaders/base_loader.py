"""Abstract base class for dataset loaders.

This module defines the common interface that all dataset loaders must implement,
enabling the evaluation framework to work with any dataset seamlessly.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseDatasetLoader(ABC):
    """Abstract base class for all dataset loaders."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize dataset loader.
        
        Args:
            data_dir: Path to dataset directory
        """
        self.data_dir = Path(data_dir) if data_dir else None
        self._tables_cache: Dict[str, Dict] = {}
        self._queries_cache: Dict[str, List[Dict]] = {}
    
    @abstractmethod
    def load_queries(self, split: str = "dev", **kwargs) -> List[Dict]:
        """
        Load queries from dataset.
        
        Args:
            split: Dataset split ('train', 'dev', 'test')
            **kwargs: Additional dataset-specific parameters
            
        Returns:
            List of query dictionaries, each containing:
            - 'question': Natural language question
            - 'sql': SQL query (format depends on dataset)
            - 'db_id' or 'table_id': Database/table identifier
            - Other dataset-specific fields
        """
        pass
    
    @abstractmethod
    def get_table_schema(self, table_id: str, split: str = "dev") -> Optional[Dict]:
        """
        Get schema for a specific table/database.
        
        Args:
            table_id: Table or database identifier
            split: Dataset split
            
        Returns:
            Table schema dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_sample(self, split: str = "dev", n: int = 10, **kwargs) -> List[Dict]:
        """
        Get a sample of queries with their schemas.
        
        Args:
            split: Dataset split
            n: Number of samples to return
            **kwargs: Additional parameters
            
        Returns:
            List of dictionaries, each containing:
            - 'query': Query dictionary with 'question' and 'sql'
            - 'table_schema' or 'database_schema': Schema dictionary
            - 'table_id' or 'db_id': Identifier
            - Other metadata
        """
        pass
    
    @abstractmethod
    def convert_sql_to_string(self, sql: Any, schema: Dict) -> str:
        """
        Convert dataset-specific SQL format to SQL string.
        
        Args:
            sql: SQL in dataset-specific format (dict, string, etc.)
            schema: Schema dictionary
            
        Returns:
            SQL query string ready for execution
        """
        pass
    
    @abstractmethod
    def get_database_path(self, db_id: str, split: str = "dev") -> Optional[Path]:
        """
        Get path to database file for a given database ID.
        
        Args:
            db_id: Database identifier
            split: Dataset split
            
        Returns:
            Path to database file or None if not found
        """
        pass
    
    def get_dataset_name(self) -> str:
        """
        Get name of the dataset.
        
        Returns:
            Dataset name string
        """
        return self.__class__.__name__.replace("Loader", "").lower()
