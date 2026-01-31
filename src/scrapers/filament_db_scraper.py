"""
Improved scraper for filament databases with anti-detection
"""

import re
from typing import List, Optional
from urllib.parse import urlencode

from src.scrapers.advanced_scraper import AdvancedScraper
from src.data.models import ScrapedData
from src.utils.logger import get_logger

logger = get_logger()


class FilamentDatabaseScraper(AdvancedScraper):
    """
    Scraper for 3dfilamentprofiles.com and similar databases
    Uses advanced anti-detection techniques
    """

    BASE_URL = "https://3dfilamentprofiles.com"

    def __init__(self):
        """Initialize scraper"""
        super().__init__()
        logger.info("FilamentDatabaseScraper initialized")

    def search(
        self,
        manufacturer: Optional[str] = None,
        material_type: Optional[str] = None,
        material_name: Optional[str] = None,
        color: Optional[str] = None
    ) -> List[ScrapedData]:
        """
        Search for filament profiles

        Args:
            manufacturer: Manufacturer name
            material_type: Material type
            material_name: Material name
            color: Color

        Returns:
            List of ScrapedData
        """
        results = []

        # Build search query
        search_terms = []
        if manufacturer:
            search_terms.append(manufacturer)
        if material_type:
            search_terms.append(material_type)
        if material_name:
            search_terms.append(material_name)

        query = " ".join(search_terms)

        if not query:
            logger.warning("No search terms provided")
            return results

        logger.info(f"Searching FilamentDB for: {query}")

        # Try multiple search strategies
        results.extend(self._search_direct(query, manufacturer, material_type))
        results.extend(self._search_api(query, manufacturer, material_type))

        logger.info(f"Found {len(results)} profiles from FilamentDB")
        return results

    def _search_direct(
        self,
        query: str,
        manufacturer: Optional[str],
        material_type: Optional[str]
    ) -> List[ScrapedData]:
        """
        Try direct HTML scraping

        Args:
            query: Search query
            manufacturer: Manufacturer
            material_type: Material type

        Returns:
            List of ScrapedData
        """
        results = []

        # Try search page
        search_url = f"{self.BASE_URL}/search?q={query.replace(' ', '+')}"

        html = self.fetch_url(search_url, use_cache=True)
        if not html:
            logger.debug("Direct search failed")
            return results

        soup = self.parse_html(html)
        if not soup:
            return results

        # Try to find filament entries
        # Note: This will need to be customized based on actual site structure
        entries = soup.find_all(['div', 'article', 'tr'], class_=re.compile(r'filament|profile|entry', re.I))

        for entry in entries:
            try:
                scraped = self._parse_entry(entry, manufacturer, material_type)
                if scraped:
                    results.append(scraped)
            except Exception as e:
                logger.debug(f"Failed to parse entry: {e}")

        return results

    def _search_api(
        self,
        query: str,
        manufacturer: Optional[str],
        material_type: Optional[str]
    ) -> List[ScrapedData]:
        """
        Try to find and use an API endpoint

        Args:
            query: Search query
            manufacturer: Manufacturer
            material_type: Material type

        Returns:
            List of ScrapedData
        """
        results = []

        # Common API endpoint patterns
        api_endpoints = [
            f"{self.BASE_URL}/api/search",
            f"{self.BASE_URL}/api/filaments",
            f"{self.BASE_URL}/api/profiles",
        ]

        params = {'q': query}
        if manufacturer:
            params['manufacturer'] = manufacturer
        if material_type:
            params['type'] = material_type

        for endpoint in api_endpoints:
            try:
                api_url = f"{endpoint}?{urlencode(params)}"
                response = self.fetch_url(api_url, use_cache=True)

                if response:
                    # Try to parse as JSON
                    import json
                    data = json.loads(response)

                    if isinstance(data, list):
                        for item in data:
                            scraped = self._parse_api_result(item, manufacturer, material_type)
                            if scraped:
                                results.append(scraped)
                    elif isinstance(data, dict) and 'results' in data:
                        for item in data['results']:
                            scraped = self._parse_api_result(item, manufacturer, material_type)
                            if scraped:
                                results.append(scraped)

                    if results:
                        logger.info(f"API endpoint {endpoint} returned {len(results)} results")
                        break

            except Exception as e:
                logger.debug(f"API endpoint {endpoint} failed: {e}")
                continue

        return results

    def _parse_entry(
        self,
        entry,
        manufacturer: Optional[str],
        material_type: Optional[str]
    ) -> Optional[ScrapedData]:
        """
        Parse an HTML entry element

        Args:
            entry: BeautifulSoup element
            manufacturer: Manufacturer
            material_type: Material type

        Returns:
            ScrapedData or None
        """
        try:
            scraped = ScrapedData(
                source="3D Filament Profiles",
                url=self.BASE_URL,
                manufacturer=manufacturer,
                material_type=material_type,
                confidence=0.6  # Medium confidence for scraped data
            )

            # Try to extract temperatures
            temp_patterns = [
                (r'nozzle.*?(\d{3})[°\s]*[CF]', 'nozzle'),
                (r'extruder.*?(\d{3})[°\s]*[CF]', 'nozzle'),
                (r'bed.*?(\d{2,3})[°\s]*[CF]', 'bed'),
                (r'hotend.*?(\d{3})[°\s]*[CF]', 'nozzle'),
            ]

            text = entry.get_text().lower()
            for pattern, temp_type in temp_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        temp = int(matches[0])
                        if 150 <= temp <= 300:  # Sanity check
                            scraped.temperatures[temp_type] = temp
                    except ValueError:
                        pass

            # Only return if we found something useful
            if scraped.temperatures:
                return scraped

        except Exception as e:
            logger.debug(f"Failed to parse entry: {e}")

        return None

    def _parse_api_result(
        self,
        item: dict,
        manufacturer: Optional[str],
        material_type: Optional[str]
    ) -> Optional[ScrapedData]:
        """
        Parse API JSON result

        Args:
            item: JSON item
            manufacturer: Manufacturer
            material_type: Material type

        Returns:
            ScrapedData or None
        """
        try:
            scraped = ScrapedData(
                source="3D Filament Profiles API",
                url=self.BASE_URL,
                manufacturer=manufacturer or item.get('manufacturer'),
                material_type=material_type or item.get('material_type'),
                confidence=0.8  # Higher confidence for API data
            )

            # Extract temperatures from common field names
            temp_fields = {
                'nozzle_temp': 'nozzle',
                'extruder_temp': 'nozzle',
                'bed_temp': 'bed',
                'nozzle_temperature': 'nozzle',
                'bed_temperature': 'bed',
            }

            for field, temp_type in temp_fields.items():
                if field in item:
                    try:
                        scraped.temperatures[temp_type] = int(item[field])
                    except (ValueError, TypeError):
                        pass

            # Extract other settings
            if 'flow_rate' in item or 'flow_ratio' in item:
                try:
                    flow = float(item.get('flow_rate', item.get('flow_ratio', 0)))
                    if flow > 0:
                        scraped.flow_settings['flow_ratio'] = flow
                except (ValueError, TypeError):
                    pass

            if scraped.temperatures:
                return scraped

        except Exception as e:
            logger.debug(f"Failed to parse API result: {e}")

        return None
