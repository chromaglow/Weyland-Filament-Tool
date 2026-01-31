"""
GitHub repository scraper for community filament profiles
"""

import re
import json
from typing import List, Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.data.models import ScrapedData
from src.utils.logger import get_logger

logger = get_logger()


class GitHubScraper(BaseScraper):
    """Scraper for GitHub community filament profile repositories"""

    REPOS = [
        "lestephen/bambu-filament",
        "dgauche/BambuStudioFilamentLibrary",
        "Doridian/BambuProfiles"
    ]

    def get_source_name(self) -> str:
        """Get the name of this data source"""
        return "GitHub Community"

    def search(
        self,
        manufacturer: Optional[str] = None,
        material_type: Optional[str] = None,
        material_name: Optional[str] = None,
        color: Optional[str] = None
    ) -> List[ScrapedData]:
        """
        Search GitHub repos for filament profiles

        Args:
            manufacturer: Manufacturer name
            material_type: Material type (PLA, PETG, etc.)
            material_name: Specific material name
            color: Filament color

        Returns:
            List of ScrapedData objects
        """
        results = []

        logger.info(f"Searching GitHub repos for: {manufacturer} {material_type} {material_name}")

        for repo in self.REPOS:
            try:
                repo_results = self._search_repo(repo, manufacturer, material_type, material_name, color)
                results.extend(repo_results)
            except Exception as e:
                logger.error(f"Failed to search {repo}: {e}")

        logger.info(f"Found {len(results)} profiles from GitHub")
        return results

    def _search_repo(
        self,
        repo: str,
        manufacturer: Optional[str],
        material_type: Optional[str],
        material_name: Optional[str],
        color: Optional[str]
    ) -> List[ScrapedData]:
        """
        Search a specific GitHub repository

        Args:
            repo: Repository in format "owner/name"
            manufacturer: Manufacturer name
            material_type: Material type
            material_name: Material name
            color: Color

        Returns:
            List of ScrapedData from this repo
        """
        results = []

        # Get repository file list via GitHub API
        api_url = f"https://api.github.com/repos/{repo}/contents"

        try:
            html = self._fetch_url(api_url)
            if not html:
                return results

            files = json.loads(html)

            # Filter for JSON files
            json_files = [f for f in files if f.get('name', '').endswith('.json')]

            # Search for matching filenames
            for file_info in json_files:
                filename = file_info.get('name', '')

                # Check if filename matches search criteria
                if self._matches_search(filename, manufacturer, material_type, material_name, color):
                    # Fetch the actual file content
                    download_url = file_info.get('download_url')
                    if download_url:
                        profile_data = self._fetch_profile(download_url, filename, repo)
                        if profile_data:
                            results.append(profile_data)

        except Exception as e:
            logger.error(f"Error searching repo {repo}: {e}")

        return results

    def _matches_search(
        self,
        filename: str,
        manufacturer: Optional[str],
        material_type: Optional[str],
        material_name: Optional[str],
        color: Optional[str]
    ) -> bool:
        """
        Check if filename matches search criteria

        Args:
            filename: File name to check
            manufacturer: Manufacturer to match
            material_type: Material type to match
            material_name: Material name to match
            color: Color to match

        Returns:
            True if matches, False otherwise
        """
        filename_lower = filename.lower()

        # Check manufacturer
        if manufacturer and manufacturer.lower() not in filename_lower:
            return False

        # Check material type
        if material_type and material_type.lower() not in filename_lower:
            return False

        # Check material name (partial match)
        if material_name:
            # Split material name into words and check each
            words = material_name.lower().split()
            if not any(word in filename_lower for word in words):
                return False

        # Check color (optional - don't exclude if not found)
        # Color is often not in filename

        return True

    def _fetch_profile(
        self,
        url: str,
        filename: str,
        repo: str
    ) -> Optional[ScrapedData]:
        """
        Fetch and parse a profile JSON file

        Args:
            url: URL to the raw JSON file
            filename: Name of the file
            repo: Repository name

        Returns:
            ScrapedData object or None
        """
        try:
            content = self._fetch_url(url)
            if not content:
                return None

            profile_json = json.loads(content)

            # Extract data from the profile
            scraped = ScrapedData(
                source=f"GitHub: {repo}",
                url=url,
                manufacturer=self._extract_manufacturer(filename, profile_json),
                material_type=self._extract_material_type(filename, profile_json),
                material_name=filename.replace('.json', ''),
                confidence=0.8  # GitHub profiles are generally reliable
            )

            # Extract temperatures
            if 'nozzle_temperature' in profile_json:
                temp = profile_json['nozzle_temperature']
                if isinstance(temp, list) and temp:
                    scraped.temperatures['nozzle'] = int(temp[0])

            if 'nozzle_temperature_initial_layer' in profile_json:
                temp = profile_json['nozzle_temperature_initial_layer']
                if isinstance(temp, list) and temp:
                    scraped.temperatures['nozzle_first_layer'] = int(temp[0])

            if 'hot_plate_temp' in profile_json:
                temp = profile_json['hot_plate_temp']
                if isinstance(temp, list) and temp:
                    scraped.temperatures['bed'] = int(temp[0])

            # Extract flow settings
            if 'filament_flow_ratio' in profile_json:
                flow = profile_json['filament_flow_ratio']
                if isinstance(flow, list) and flow:
                    scraped.flow_settings['flow_ratio'] = float(flow[0])

            if 'filament_max_volumetric_speed' in profile_json:
                speed = profile_json['filament_max_volumetric_speed']
                if isinstance(speed, list) and speed:
                    scraped.speeds['max_volumetric_speed'] = int(speed[0])

            # Extract other settings
            for key, value in profile_json.items():
                if key not in ['nozzle_temperature', 'nozzle_temperature_initial_layer',
                              'hot_plate_temp', 'filament_flow_ratio',
                              'filament_max_volumetric_speed']:
                    scraped.other_settings[key] = value

            logger.debug(f"Parsed profile from {filename}")
            return scraped

        except Exception as e:
            logger.error(f"Failed to parse profile {filename}: {e}")
            return None

    def _extract_manufacturer(self, filename: str, profile_json: dict) -> Optional[str]:
        """Extract manufacturer from filename or profile"""
        # Try to extract from filename
        # Common patterns: "Manufacturer Material.json"
        name = filename.replace('.json', '')
        parts = name.split()
        if parts:
            return parts[0]
        return None

    def _extract_material_type(self, filename: str, profile_json: dict) -> Optional[str]:
        """Extract material type from filename or profile"""
        filename_lower = filename.lower()

        # Check for material types in filename
        materials = ['pla', 'petg', 'abs', 'tpu', 'asa', 'pa', 'pc']
        for material in materials:
            if material in filename_lower:
                return material.upper()

        # Try to extract from inherits field
        inherits = profile_json.get('inherits', '')
        if inherits:
            for material in materials:
                if material in inherits.lower():
                    return material.upper()

        return None
