"""
Bambu Studio integration utilities
"""

import os
import shutil
import psutil
from pathlib import Path
from typing import Optional, List
from .logger import get_logger

logger = get_logger()


class BambuStudioIntegration:
    """Handle integration with Bambu Studio"""

    def __init__(self):
        """Initialize Bambu Studio integration"""
        self.bambu_studio_path = self._find_bambu_studio_path()
        self.device_ids = self._find_device_ids()

    def _find_bambu_studio_path(self) -> Optional[Path]:
        """
        Find Bambu Studio user data directory

        Returns:
            Path to BambuStudio user directory or None
        """
        # Windows path
        appdata = os.getenv('APPDATA')
        if appdata:
            bambu_path = Path(appdata) / "BambuStudio"
            if bambu_path.exists():
                logger.info(f"Found Bambu Studio directory: {bambu_path}")
                return bambu_path

        # Alternative locations
        alternative_paths = [
            Path.home() / "AppData" / "Roaming" / "BambuStudio",
            Path.home() / ".config" / "BambuStudio",  # Linux
            Path.home() / "Library" / "Application Support" / "BambuStudio",  # macOS
        ]

        for path in alternative_paths:
            if path.exists():
                logger.info(f"Found Bambu Studio directory: {path}")
                return path

        logger.warning("Bambu Studio directory not found")
        return None

    def _find_device_ids(self) -> List[str]:
        """
        Find all device IDs in Bambu Studio user directory

        Returns:
            List of device IDs
        """
        device_ids = []

        if not self.bambu_studio_path:
            return device_ids

        user_path = self.bambu_studio_path / "user"
        if not user_path.exists():
            return device_ids

        # Scan for device ID directories
        for item in user_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it has a filament subdirectory
                filament_path = item / "filament"
                if filament_path.exists():
                    device_ids.append(item.name)
                    logger.debug(f"Found device ID: {item.name}")

        if device_ids:
            logger.info(f"Found {len(device_ids)} device ID(s)")
        else:
            logger.warning("No device IDs found in Bambu Studio directory")

        return device_ids

    def get_filament_directories(self) -> List[Path]:
        """
        Get all filament directories for all devices

        Returns:
            List of filament directory paths
        """
        directories = []

        if not self.bambu_studio_path:
            return directories

        for device_id in self.device_ids:
            filament_path = self.bambu_studio_path / "user" / device_id / "filament"
            if filament_path.exists():
                directories.append(filament_path)

        return directories

    def import_profile(self, profile_path: Path, device_id: Optional[str] = None) -> bool:
        """
        Import a profile to Bambu Studio

        Args:
            profile_path: Path to the profile JSON file
            device_id: Specific device ID to import to (uses first found if None)

        Returns:
            True if successful, False otherwise
        """
        if not profile_path.exists():
            logger.error(f"Profile file not found: {profile_path}")
            return False

        # Get target directories
        if device_id:
            # Use specific device
            target_dir = self.bambu_studio_path / "user" / device_id / "filament"
            if not target_dir.exists():
                logger.error(f"Device ID not found: {device_id}")
                return False
            target_dirs = [target_dir]
        else:
            # Use all found devices
            target_dirs = self.get_filament_directories()

        if not target_dirs:
            logger.error("No Bambu Studio filament directories found")
            return False

        # Copy to all target directories
        success = True
        for target_dir in target_dirs:
            try:
                target_file = target_dir / profile_path.name
                shutil.copy2(profile_path, target_file)
                logger.info(f"Imported profile to: {target_file}")
            except Exception as e:
                logger.error(f"Failed to import to {target_dir}: {e}")
                success = False

        return success

    def is_bambu_studio_running(self) -> bool:
        """
        Check if Bambu Studio is currently running

        Returns:
            True if running, False otherwise
        """
        process_names = ["bambu-studio.exe", "bambu_studio.exe", "BambuStudio.exe"]

        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() in [p.lower() for p in process_names]:
                    logger.info("Bambu Studio is running")
                    return True
        except Exception as e:
            logger.error(f"Error checking processes: {e}")

        return False

    def get_default_device_id(self) -> Optional[str]:
        """
        Get the default/first device ID

        Returns:
            Device ID or None
        """
        if self.device_ids:
            return self.device_ids[0]
        return None

    def refresh_device_ids(self):
        """Refresh the list of device IDs"""
        self.device_ids = self._find_device_ids()


# Global instance
_bambu_integration: Optional[BambuStudioIntegration] = None


def get_bambu_integration() -> BambuStudioIntegration:
    """
    Get the global Bambu Studio integration instance

    Returns:
        BambuStudioIntegration instance
    """
    global _bambu_integration
    if _bambu_integration is None:
        _bambu_integration = BambuStudioIntegration()
    return _bambu_integration
