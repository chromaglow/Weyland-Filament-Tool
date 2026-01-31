"""
Profile builder for creating Bambu Studio filament profiles
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.data.models import FilamentProfile, MaterialSettings, ScrapedData
from src.generator.templates import get_template_manager
from src.generator.id_generator import get_id_generator
from src.utils.logger import get_logger
from src.utils.config import get_config
from src.utils.bambu_studio import get_bambu_integration

logger = get_logger()


class ProfileBuilder:
    """Builds Bambu Studio filament profiles from templates and scraped data"""

    def __init__(self):
        """Initialize profile builder"""
        self.template_manager = get_template_manager()
        self.id_generator = get_id_generator()
        self.config = get_config()

    def build_profile(
        self,
        name: str,
        material_type: str,
        manufacturer: str,
        scraped_data: Optional[List[ScrapedData]] = None,
        manual_overrides: Optional[Dict[str, Any]] = None
    ) -> FilamentProfile:
        """
        Build a complete filament profile

        Args:
            name: Profile name (e.g., "Overture PLA Black")
            material_type: Material type (e.g., "pla", "petg")
            manufacturer: Manufacturer name
            scraped_data: List of scraped data from various sources
            manual_overrides: Manual override settings

        Returns:
            Complete FilamentProfile object
        """
        logger.info(f"Building profile: {name} ({material_type})")

        # Get base template
        template = self.template_manager.get_template(material_type)
        if not template:
            logger.warning(f"No template found for {material_type}, using defaults")
            template = {}

        # Create material settings
        settings = self._merge_settings(template, scraped_data, manual_overrides)

        # Generate IDs
        filament_id = self.id_generator.generate_filament_id(material_type)
        setting_id = self.id_generator.generate_setting_id(material_type, manufacturer)

        # Get inheritance base
        inherits = self.template_manager.get_base_profile_name(material_type)

        # Build profile
        profile = FilamentProfile(
            name=name,
            material_type=material_type.upper(),
            manufacturer=manufacturer,
            inherits=inherits,
            filament_settings_id=[name],
            filament_id=filament_id,
            setting_id=setting_id,
            settings=settings
        )

        # Add source URLs if available
        if scraped_data:
            profile.source_urls = [data.url for data in scraped_data if data.url]

        logger.info(f"Profile built: {name} (ID: {filament_id})")
        return profile

    def _merge_settings(
        self,
        template: Dict[str, Any],
        scraped_data: Optional[List[ScrapedData]],
        manual_overrides: Optional[Dict[str, Any]]
    ) -> MaterialSettings:
        """
        Merge settings from template, scraped data, and manual overrides

        Priority (highest to lowest):
        1. Manual overrides
        2. Scraped data (highest confidence first)
        3. Template defaults

        Args:
            template: Base template data
            scraped_data: List of scraped data
            manual_overrides: Manual override settings

        Returns:
            Merged MaterialSettings object
        """
        # Start with template
        merged = MaterialSettings()

        # Apply template values
        self._apply_dict_to_settings(merged, template)

        # Apply scraped data (sorted by confidence)
        if scraped_data:
            sorted_data = sorted(scraped_data, key=lambda x: x.confidence, reverse=True)
            for data in sorted_data:
                settings = data.to_material_settings()
                self._apply_settings(merged, settings, overwrite=False)

        # Apply manual overrides (highest priority)
        if manual_overrides:
            self._apply_dict_to_settings(merged, manual_overrides)

        return merged

    def _apply_dict_to_settings(self, settings: MaterialSettings, data: Dict[str, Any]):
        """
        Apply dictionary values to MaterialSettings object

        Args:
            settings: MaterialSettings object to update
            data: Dictionary of settings
        """
        for key, value in data.items():
            if hasattr(settings, key):
                # Convert string arrays back to proper types if needed
                if isinstance(value, list) and len(value) > 0:
                    # Try to convert to int/float if possible
                    try:
                        if '.' in str(value[0]):
                            value = [float(v) for v in value]
                        else:
                            value = [int(v) for v in value]
                    except (ValueError, TypeError):
                        pass  # Keep as string list

                setattr(settings, key, value)
            else:
                # Add to additional_settings
                settings.additional_settings[key] = value

    def _apply_settings(
        self,
        target: MaterialSettings,
        source: MaterialSettings,
        overwrite: bool = True
    ):
        """
        Apply settings from source to target

        Args:
            target: Target MaterialSettings
            source: Source MaterialSettings
            overwrite: Whether to overwrite existing values
        """
        for key, value in source.__dict__.items():
            if key == 'additional_settings':
                target.additional_settings.update(value)
            elif value is not None:
                if overwrite or getattr(target, key) is None:
                    setattr(target, key, value)

    def save_profile(self, profile: FilamentProfile, output_path: Optional[Path] = None) -> Path:
        """
        Save profile to JSON file

        Args:
            profile: FilamentProfile to save
            output_path: Output file path. If None, uses default location

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_dir = self.config.get_output_path()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{profile.name}.json"

        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to Bambu JSON format
        profile_json = profile.to_bambu_json()

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile_json, f, indent=2, ensure_ascii=False)

        logger.info(f"Profile saved to: {output_path}")
        return output_path

    def load_profile(self, file_path: Path) -> FilamentProfile:
        """
        Load profile from JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            FilamentProfile object
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract basic info
        name = data.get("name", "Unknown")
        inherits = data.get("inherits", "Generic PLA")

        # Determine material type from inherits
        material_type = inherits.replace("Generic ", "").strip()

        profile = FilamentProfile(
            name=name,
            material_type=material_type,
            inherits=inherits,
            from_source=data.get("from", "User"),
            version=data.get("version", "1.6.0.2"),
            filament_settings_id=data.get("filament_settings_id", [name]),
            filament_id=data.get("filament_id"),
            setting_id=data.get("setting_id"),
            instantiation=data.get("instantiation", "true")
        )

        # Load settings
        settings = MaterialSettings()
        self._apply_dict_to_settings(settings, data)
        profile.settings = settings

        return profile

    def import_to_bambu_studio(
        self,
        profile: FilamentProfile,
        device_id: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Save and import profile directly to Bambu Studio

        Args:
            profile: FilamentProfile to import
            device_id: Specific device ID (uses default if None)

        Returns:
            (success, message) tuple
        """
        bambu = get_bambu_integration()

        # Check if Bambu Studio directory exists
        if not bambu.bambu_studio_path:
            return (False, "Bambu Studio directory not found. Please install Bambu Studio.")

        # Check for device IDs
        if not bambu.device_ids:
            return (False, "No Bambu Studio devices found. Please set up a printer in Bambu Studio first.")

        # Save to temporary location first
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"{profile.name}.json"

        try:
            # Save profile
            self.save_profile(profile, temp_path)

            # Import to Bambu Studio
            success = bambu.import_profile(temp_path, device_id)

            if success:
                message = f"Profile imported successfully to Bambu Studio!\n"
                if len(bambu.device_ids) > 1:
                    message += f"Imported to {len(bambu.device_ids)} device(s)."
                else:
                    message += f"Imported to device: {bambu.device_ids[0]}"

                # Check if Bambu Studio is running
                if bambu.is_bambu_studio_running():
                    message += "\n\nNote: Bambu Studio is running. Please restart it to see the new profile."

                logger.info(f"Profile imported to Bambu Studio: {profile.name}")
                return (True, message)
            else:
                return (False, "Failed to import profile to Bambu Studio.")

        except Exception as e:
            logger.error(f"Error importing profile: {e}")
            return (False, f"Error importing profile: {str(e)}")

        finally:
            # Clean up temp file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
