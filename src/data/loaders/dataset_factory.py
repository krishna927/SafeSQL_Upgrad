"""Dataset loader factory for creating appropriate loaders based on dataset name."""

from pathlib import Path
from typing import Optional, Type

from .base_loader import BaseDatasetLoader
from .wikisql_value_loader import WikiSQLValueLoader
from .spider_loader import SpiderLoader
from .bird_loader import BIRDLoader

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass


def create_loader(dataset_name: str, data_dir: Optional[Path] = None) -> BaseDatasetLoader:
    """
    Create appropriate dataset loader based on dataset name.
    
    Args:
        dataset_name: Name of dataset ('wikisql', 'spider', 'bird', etc.)
        data_dir: Optional path to dataset directory
        
    Returns:
        Dataset loader instance
        
    Raises:
        ValueError: If dataset name is not recognized
    """
    dataset_name_lower = dataset_name.lower()
    
    if dataset_name_lower in ['wikisql', 'wikisql_value', 'wikisql-value']:
        return WikiSQLValueLoader(data_dir)
    elif dataset_name_lower == 'spider':
        return SpiderLoader(data_dir)
    elif dataset_name_lower == 'bird':
        return BIRDLoader(data_dir)
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}. Supported: 'wikisql', 'spider', 'bird'")
