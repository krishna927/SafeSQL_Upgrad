"""Script to preprocess and serialize WikiSQL_VALUE schemas.

This script extracts schemas from WikiSQL_VALUE dataset and saves them
in standardized JSON format for use by SafeSQL framework.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.preprocessors.schema_serializer import WikiSQLValueSchemaSerializer
from src.utils.logger import setup_logger, get_logger

# Setup logging
setup_logger("safesql", level="INFO", console=True)
logger = get_logger(__name__)


def main():
    """Main function to serialize WikiSQL_VALUE schemas."""
    logger.info("=" * 60)
    logger.info("WikiSQL_VALUE Schema Serialization")
    logger.info("=" * 60)
    
    serializer = WikiSQLValueSchemaSerializer()
    
    # Serialize all splits
    logger.info("\nSerializing schemas for all splits (train, dev, test)...")
    all_schemas = serializer.serialize_all_splits()
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Serialization Summary")
    logger.info("=" * 60)
    
    for split, schemas in all_schemas.items():
        logger.info(f"{split}: {len(schemas)} schemas serialized")
    
    total_schemas = sum(len(schemas) for schemas in all_schemas.values())
    logger.info(f"\nTotal: {total_schemas} schemas across all splits")
    
    # Show sample schema
    if all_schemas.get('dev'):
        first_table_id = list(all_schemas['dev'].keys())[0]
        sample_schema = all_schemas['dev'][first_table_id]
        logger.info(f"\nSample schema ({first_table_id}):")
        logger.info(f"  Table: {sample_schema['table_name']}")
        logger.info(f"  Columns: {len(sample_schema['columns'])}")
        logger.info(f"  Column names: {[col['name'] for col in sample_schema['columns']]}")
    
    logger.info("\nStatus: Schema serialization complete")
    logger.info(f"Schema files saved to: {project_root / 'data' / 'schemas' / 'wikisql_value'}")


if __name__ == "__main__":
    main()
