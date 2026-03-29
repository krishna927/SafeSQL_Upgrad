"""Base model interface for LLM integration."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseModel(ABC):
    """Abstract base class for LLM models."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the base model.
        
        Args:
            config: Model configuration dictionary
        """
        self.config = config or {}
        self.logger = logger
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate SQL query from natural language prompt.
        
        Args:
            prompt: Natural language query
            schema: Database schema information
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters
            
        Returns:
            Generated SQL query string
        """
        pass
    
    @abstractmethod
    def generate_batch(
        self,
        prompts: List[str],
        schemas: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[str]:
        """
        Generate SQL queries for multiple prompts.
        
        Args:
            prompts: List of natural language queries
            schemas: List of database schemas (one per prompt)
            **kwargs: Additional generation parameters
            
        Returns:
            List of generated SQL queries
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate model configuration.
        
        Returns:
            True if configuration is valid
        """
        return True
    
    def get_model_info(self) -> Dict:
        """
        Get model information.
        
        Returns:
            Dictionary with model metadata
        """
        return {
            "model_type": self.__class__.__name__,
            "config": self.config
        }
