"""
ID generation for Bambu Studio filament profiles
"""

import hashlib
from typing import Dict, Set
from src.utils.logger import get_logger

logger = get_logger()


class IDGenerator:
    """Generates unique filament_id and setting_id for profiles"""

    # Material type to ID prefix mapping
    MATERIAL_PREFIXES: Dict[str, str] = {
        "pla": "GFL",
        "petg": "GFG",
        "abs": "GFA",
        "tpu": "GFU",
        "pa": "GFN",  # Nylon/Polyamide
        "pc": "GFC",  # Polycarbonate
        "asa": "GFS",  # ASA
        "pva": "GFV",  # PVA support material
        "cf": "GFT",   # Carbon fiber composites
    }

    def __init__(self):
        """Initialize ID generator"""
        self._used_ids: Set[str] = set()
        self._used_setting_ids: Set[str] = set()

    def generate_filament_id(self, material_type: str, custom_suffix: str = None) -> str:
        """
        Generate a filament_id based on material type

        Args:
            material_type: Material type (e.g., "pla", "petg")
            custom_suffix: Optional custom suffix (00-99)

        Returns:
            Filament ID (e.g., "GFL00", "GFG01")
        """
        material_lower = material_type.lower()
        prefix = self.MATERIAL_PREFIXES.get(material_lower, "GFX")

        if custom_suffix:
            filament_id = f"{prefix}{custom_suffix}"
        else:
            # Find next available number
            for i in range(0, 100):
                filament_id = f"{prefix}{i:02d}"
                if filament_id not in self._used_ids:
                    break
            else:
                # All IDs used, use hash-based suffix
                hash_suffix = hashlib.md5(material_type.encode()).hexdigest()[:2]
                filament_id = f"{prefix}{hash_suffix}"

        self._used_ids.add(filament_id)
        logger.debug(f"Generated filament_id: {filament_id}")
        return filament_id

    def generate_setting_id(
        self,
        material_type: str,
        manufacturer: str,
        counter: int = 1
    ) -> str:
        """
        Generate a setting_id based on material, manufacturer, and counter

        Format: {filament_id_prefix}S{filament_suffix}_{Manufacturer}_{counter:02d}
        Example: GFSL00_Overture_01

        Args:
            material_type: Material type (e.g., "pla", "petg")
            manufacturer: Manufacturer name
            counter: Counter for multiple profiles from same manufacturer

        Returns:
            Setting ID (e.g., "GFSL00_Overture_01")
        """
        material_lower = material_type.lower()
        prefix = self.MATERIAL_PREFIXES.get(material_lower, "GFX")

        # Clean manufacturer name (remove spaces, special chars)
        clean_manufacturer = "".join(c for c in manufacturer if c.isalnum())

        # Find next available counter
        for i in range(counter, 100):
            setting_id = f"{prefix}S00_{clean_manufacturer}_{i:02d}"
            if setting_id not in self._used_setting_ids:
                self._used_setting_ids.add(setting_id)
                logger.debug(f"Generated setting_id: {setting_id}")
                return setting_id

        # Fallback with hash
        hash_suffix = hashlib.md5(f"{manufacturer}{counter}".encode()).hexdigest()[:2]
        setting_id = f"{prefix}S{hash_suffix}_{clean_manufacturer}_99"
        self._used_setting_ids.add(setting_id)
        return setting_id

    def register_existing_id(self, filament_id: str, setting_id: str = None):
        """
        Register existing IDs to avoid collisions

        Args:
            filament_id: Existing filament ID
            setting_id: Existing setting ID (optional)
        """
        if filament_id:
            self._used_ids.add(filament_id)

        if setting_id:
            self._used_setting_ids.add(setting_id)

    def reset(self):
        """Reset all tracked IDs"""
        self._used_ids.clear()
        self._used_setting_ids.clear()


# Global ID generator instance
_id_generator: IDGenerator = None


def get_id_generator() -> IDGenerator:
    """
    Get the global ID generator instance

    Returns:
        IDGenerator instance
    """
    global _id_generator
    if _id_generator is None:
        _id_generator = IDGenerator()
    return _id_generator
