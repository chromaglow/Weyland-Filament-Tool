"""
Template management for base filament profiles
"""

import json
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger()


class TemplateManager:
    """Manages base filament profile templates"""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template manager

        Args:
            templates_dir: Path to templates directory. If None, uses default
        """
        if templates_dir is None:
            project_root = Path(__file__).parent.parent.parent
            templates_dir = project_root / "resources" / "templates"

        self.templates_dir = Path(templates_dir)
        self._templates: Dict[str, Dict] = {}
        self.load_templates()

    def load_templates(self):
        """Load all template JSON files from the templates directory"""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                template_name = template_file.stem
                self._templates[template_name] = template_data
                logger.debug(f"Loaded template: {template_name}")

            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")

        logger.info(f"Loaded {len(self._templates)} templates")

    def get_template(self, material_type: str) -> Optional[Dict]:
        """
        Get template for a material type

        Args:
            material_type: Material type (e.g., "pla", "petg", "abs", "tpu")

        Returns:
            Template dictionary or None if not found
        """
        template_key = f"generic_{material_type.lower()}"

        if template_key in self._templates:
            return self._templates[template_key].copy()

        logger.warning(f"Template not found for material: {material_type}")
        return None

    def get_base_profile_name(self, material_type: str) -> str:
        """
        Get the base profile name for inheritance

        Args:
            material_type: Material type (e.g., "pla", "petg")

        Returns:
            Base profile name (e.g., "Generic PLA")
        """
        template = self.get_template(material_type)
        if template and "name" in template:
            return template["name"]

        # Fallback
        return f"Generic {material_type.upper()}"

    def list_templates(self) -> list[str]:
        """
        Get list of available template names

        Returns:
            List of template names
        """
        return list(self._templates.keys())


# Global template manager instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """
    Get the global template manager instance

    Returns:
        TemplateManager instance
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
