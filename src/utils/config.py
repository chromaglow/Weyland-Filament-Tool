"""
Configuration management for Bambu Filament Tool
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Application configuration manager"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_path: Path to settings.json file. If None, uses default location
        """
        if config_path is None:
            # Default to config/settings.json relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "settings.json"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

    def save(self):
        """Save configuration to JSON file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., "scraper.timeout")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key (e.g., "scraper.timeout")
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @property
    def scraper_config(self) -> Dict[str, Any]:
        """Get scraper configuration"""
        return self.get("scraper", {})

    @property
    def cache_config(self) -> Dict[str, Any]:
        """Get cache configuration"""
        return self.get("cache", {})

    @property
    def output_config(self) -> Dict[str, Any]:
        """Get output configuration"""
        return self.get("output", {})

    @property
    def materials_config(self) -> Dict[str, Any]:
        """Get materials configuration"""
        return self.get("materials", {})

    @property
    def sources_config(self) -> Dict[str, Any]:
        """Get sources configuration"""
        return self.get("sources", {})

    def get_material_config(self, material_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific material type

        Args:
            material_type: Material type (e.g., "pla", "petg")

        Returns:
            Material configuration or None
        """
        return self.materials_config.get(material_type.lower())

    def get_output_path(self) -> Path:
        """
        Get the default output path, expanding environment variables

        Returns:
            Path object for output directory
        """
        path_str = self.get("output.default_path", ".")
        expanded = os.path.expandvars(path_str)
        return Path(expanded)

    def is_source_enabled(self, source_name: str) -> bool:
        """
        Check if a data source is enabled

        Args:
            source_name: Name of the source (e.g., "3dfilamentprofiles")

        Returns:
            True if enabled, False otherwise
        """
        source_config = self.sources_config.get(source_name, {})
        return source_config.get("enabled", False)


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config():
    """Reload the global configuration from disk"""
    global _config_instance
    if _config_instance is not None:
        _config_instance.load()
