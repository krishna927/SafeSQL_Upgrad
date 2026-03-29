"""Configuration loader for SafeSQL framework."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages configuration from YAML files and environment variables."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing config files. Defaults to 'config' in project root.
        """
        # Load environment variables
        load_dotenv()
        
        # Determine config directory
        if config_dir is None:
            # Assume config is in safesql/config relative to this file
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"
        else:
            config_dir = Path(config_dir)
        
        self.config_dir = config_dir
        self._settings: Dict[str, Any] = {}
        self._safety_policies: Dict[str, Any] = {}
        
        # Load configurations
        self._load_settings()
        self._load_safety_policies()
    
    def _load_settings(self) -> None:
        """Load settings.yaml file."""
        settings_file = self.config_dir / "settings.yaml"
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                self._settings = yaml.safe_load(f) or {}
            # Substitute environment variables
            self._substitute_env_vars(self._settings)
        else:
            raise FileNotFoundError(f"Settings file not found: {settings_file}")
    
    def _load_safety_policies(self) -> None:
        """Load safety_policies.yaml file."""
        policies_file = self.config_dir / "safety_policies.yaml"
        if policies_file.exists():
            with open(policies_file, 'r', encoding='utf-8') as f:
                self._safety_policies = yaml.safe_load(f) or {}
        else:
            raise FileNotFoundError(f"Safety policies file not found: {policies_file}")
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> None:
        """Recursively substitute environment variables in config values."""
        for key, value in config.items():
            if isinstance(value, dict):
                self._substitute_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract environment variable name
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'models.gpt4.temperature')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self._settings.copy()
    
    def get_safety_policies(self) -> Dict[str, Any]:
        """Get all safety policies."""
        return self._safety_policies.copy()
    
    def reload(self) -> None:
        """Reload configuration files."""
        self._load_settings()
        self._load_safety_policies()


# Global config instance
_config_instance: Optional[ConfigLoader] = None


def get_config(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Get or create the global configuration instance.
    
    Args:
        config_dir: Directory containing config files
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_dir)
    return _config_instance
