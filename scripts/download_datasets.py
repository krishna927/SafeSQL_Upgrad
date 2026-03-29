"""Automated script to download all datasets for SafeSQL research."""

import argparse
import os
import sys
from pathlib import Path
import json
import subprocess
from typing import List, Optional

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.logger import setup_logger, get_logger
from utils.config_loader import ConfigLoader

logger = get_logger(__name__)


class DatasetDownloader:
    """Handles downloading of all required datasets."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize dataset downloader.
        
        Args:
            base_dir: Base directory for datasets. Defaults to project_root/data/datasets
        """
        if base_dir is None:
            base_dir = project_root / "data" / "datasets"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        try:
            self.config = ConfigLoader()
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")
            self.config = None
    
    def download_spider(self) -> bool:
        """
        Download Spider dataset.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Downloading Spider Dataset")
        logger.info("=" * 60)
        
        spider_dir = self.base_dir / "spider"
        spider_dir.mkdir(exist_ok=True)
        
        logger.info("Spider dataset requires manual download:")
        logger.info("1. Visit: https://yale-lily.github.io/spider")
        logger.info("2. Download the following files:")
        logger.info("   - train_spider.json")
        logger.info("   - dev.json")
        logger.info("   - tables.json")
        logger.info("   - database.zip (200 databases)")
        logger.info(f"3. Extract to: {spider_dir}")
        
        # Try GitHub clone as alternative
        logger.info("\nAttempting GitHub clone as alternative...")
        try:
            if not (spider_dir / ".git").exists():
                subprocess.run(
                    ["git", "clone", "https://github.com/taoyds/spider.git", str(spider_dir)],
                    check=True,
                    capture_output=True
                )
                logger.info("✅ Spider dataset cloned successfully!")
                return True
            else:
                logger.info("Spider repository already exists. Skipping clone.")
                return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git clone failed: {e}")
            logger.info("Please download manually from the website.")
            return False
        except FileNotFoundError:
            logger.warning("Git not found. Please install Git or download manually.")
            return False
    
    def download_bird(self) -> bool:
        """
        Download BIRD dataset.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Downloading BIRD Dataset")
        logger.info("=" * 60)
        
        bird_dir = self.base_dir / "bird"
        bird_dir.mkdir(exist_ok=True)
        
        logger.info("BIRD dataset is large (~10-15 GB). Downloading...")
        
        try:
            if not (bird_dir / ".git").exists():
                subprocess.run(
                    ["git", "clone", "https://github.com/google/bigbench-bird.git", str(bird_dir)],
                    check=True
                )
                logger.info("✅ BIRD dataset cloned successfully!")
                return True
            else:
                logger.info("BIRD repository already exists. Skipping clone.")
                return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e}")
            logger.info("Please download manually from: https://bird-bench.github.io/")
            return False
        except FileNotFoundError:
            logger.warning("Git not found. Please install Git or download manually.")
            return False
    
    def download_huggingface_datasets(self) -> bool:
        """
        Download HuggingFace datasets (SynQL-Spider-Train and WikiSQL_VALUE).
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Downloading HuggingFace Datasets")
        logger.info("=" * 60)
        
        try:
            from datasets import load_dataset
        except ImportError:
            logger.error("datasets library not found. Install with: pip install datasets")
            return False
        
        # Check for HuggingFace token
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            logger.warning("HUGGINGFACE_TOKEN not set. Some datasets may require authentication.")
            logger.info("Set it in .env file or export HUGGINGFACE_TOKEN=your_token")
        
        success = True
        
        # Download SynQL-Spider-Train
        logger.info("\nDownloading SynQL-Spider-Train...")
        try:
            synql_dir = self.base_dir / "synql_spider_train"
            synql_dir.mkdir(exist_ok=True)
            
            dataset = load_dataset(
                "semiotic/SynQL-Spider-Train",
                token=hf_token if hf_token else None
            )
            dataset.save_to_disk(str(synql_dir))
            logger.info(f"✅ SynQL-Spider-Train downloaded to {synql_dir}")
        except Exception as e:
            logger.error(f"Failed to download SynQL-Spider-Train: {e}")
            success = False
        
        # Download WikiSQL_VALUE
        logger.info("\nDownloading WikiSQL_VALUE...")
        try:
            wikisql_dir = self.base_dir / "wikisql_value"
            wikisql_dir.mkdir(exist_ok=True)
            
            dataset = load_dataset(
                "SALT-NLP/wikisql_VALUE",
                token=hf_token if hf_token else None
            )
            dataset.save_to_disk(str(wikisql_dir))
            logger.info(f"✅ WikiSQL_VALUE downloaded to {wikisql_dir}")
        except Exception as e:
            logger.error(f"Failed to download WikiSQL_VALUE: {e}")
            success = False
        
        return success
    
    def verify_downloads(self) -> dict:
        """
        Verify that all downloaded datasets are present.
        
        Returns:
            Dictionary with verification results
        """
        logger.info("=" * 60)
        logger.info("Verifying Downloads")
        logger.info("=" * 60)
        
        results = {
            "spider": False,
            "bird": False,
            "synql_spider": False,
            "wikisql_value": False
        }
        
        # Check Spider
        spider_dir = self.base_dir / "spider"
        if spider_dir.exists():
            required_files = ["train_spider.json", "dev.json", "tables.json"]
            has_files = all((spider_dir / f).exists() for f in required_files)
            has_databases = (spider_dir / "database").exists()
            results["spider"] = has_files and has_databases
            status = "✅" if results["spider"] else "❌"
            logger.info(f"{status} Spider: Files={has_files}, Databases={has_databases}")
        
        # Check BIRD
        bird_dir = self.base_dir / "bird"
        if bird_dir.exists():
            has_train = (bird_dir / "train" / "train.json").exists()
            has_dev = (bird_dir / "dev" / "dev.json").exists()
            has_databases = (bird_dir / "dev_databases").exists()
            results["bird"] = has_train and has_dev and has_databases
            status = "✅" if results["bird"] else "❌"
            logger.info(f"{status} BIRD: Train={has_train}, Dev={has_dev}, DBs={has_databases}")
        
        # Check SynQL-Spider-Train
        synql_dir = self.base_dir / "synql_spider_train"
        results["synql_spider"] = synql_dir.exists() and any(synql_dir.iterdir())
        status = "✅" if results["synql_spider"] else "❌"
        logger.info(f"{status} SynQL-Spider-Train: {results['synql_spider']}")
        
        # Check WikiSQL_VALUE
        wikisql_dir = self.base_dir / "wikisql_value"
        results["wikisql_value"] = wikisql_dir.exists() and any(wikisql_dir.iterdir())
        status = "✅" if results["wikisql_value"] else "❌"
        logger.info(f"{status} WikiSQL_VALUE: {results['wikisql_value']}")
        
        return results
    
    def print_summary(self):
        """Print download summary and next steps."""
        logger.info("\n" + "=" * 60)
        logger.info("Download Summary")
        logger.info("=" * 60)
        logger.info(f"Base directory: {self.base_dir}")
        logger.info("\nNext steps:")
        logger.info("1. Verify all datasets are downloaded correctly")
        logger.info("2. Run preprocessing scripts (to be implemented)")
        logger.info("3. Extract schemas from databases")
        logger.info("4. Annotate queries with safety labels")


def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download datasets for SafeSQL research"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all datasets"
    )
    parser.add_argument(
        "--spider",
        action="store_true",
        help="Download Spider dataset"
    )
    parser.add_argument(
        "--bird",
        action="store_true",
        help="Download BIRD dataset"
    )
    parser.add_argument(
        "--huggingface",
        action="store_true",
        help="Download HuggingFace datasets (SynQL, WikiSQL)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing downloads"
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default=None,
        help="Base directory for datasets (default: data/datasets)"
    )
    
    args = parser.parse_args()
    
    # Set up logger
    setup_logger("safesql", level="INFO", console=True)
    
    # Initialize downloader
    base_dir = Path(args.base_dir) if args.base_dir else None
    downloader = DatasetDownloader(base_dir)
    
    # Execute downloads
    if args.verify:
        results = downloader.verify_downloads()
        all_ok = all(results.values())
        sys.exit(0 if all_ok else 1)
    
    if args.all or (not any([args.spider, args.bird, args.huggingface])):
        # Download all if --all or no specific flag
        logger.info("Downloading all datasets...")
        downloader.download_spider()
        downloader.download_bird()
        downloader.download_huggingface_datasets()
    else:
        if args.spider:
            downloader.download_spider()
        if args.bird:
            downloader.download_bird()
        if args.huggingface:
            downloader.download_huggingface_datasets()
    
    # Verify downloads
    downloader.verify_downloads()
    
    # Print summary
    downloader.print_summary()


if __name__ == "__main__":
    main()
