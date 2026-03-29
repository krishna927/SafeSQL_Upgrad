"""Schema serializer factory for creating appropriate serializers based on dataset."""

from pathlib import Path
from typing import Optional

from .schema_serializer import WikiSQLValueSchemaSerializer
from .spider_schema_serializer import SpiderSchemaSerializer
from .bird_schema_serializer import BIRDSchemaSerializer

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass


def create_serializer(dataset_name: str, data_dir: Optional[Path] = None):
    """
    Create appropriate schema serializer based on dataset name.
    
    Args:
        dataset_name: Name of dataset ('wikisql', 'spider', 'bird', etc.)
        data_dir: Optional path to dataset directory
        
    Returns:
        Schema serializer instance
        
    Raises:
        ValueError: If dataset name is not recognized
    """
    dataset_name_lower = dataset_name.lower()
    
    if dataset_name_lower in ['wikisql', 'wikisql_value', 'wikisql-value']:
        return WikiSQLValueSchemaSerializer(data_dir)
    elif dataset_name_lower == 'spider':
        return SpiderSchemaSerializer(data_dir)
    elif dataset_name_lower == 'bird':
        return BIRDSchemaSerializer(data_dir)
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}. Supported: 'wikisql', 'spider', 'bird'")
