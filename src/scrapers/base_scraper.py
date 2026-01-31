"""
Base scraper class with rate limiting and error handling
"""

import time
import requests
from abc import ABC, abstractmethod
from typing import List, Optional
from bs4 import BeautifulSoup

from src.data.models import ScrapedData
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger()


class BaseScraper(ABC):
    """Abstract base class for web scrapers"""

    def __init__(self):
        """Initialize base scraper"""
        self.config = get_config()
        self.scraper_config = self.config.scraper_config

        self.user_agent = self.scraper_config.get("user_agent", "BambuFilamentTool/1.0")
        self.timeout = self.scraper_config.get("timeout", 10)
        self.max_retries = self.scraper_config.get("max_retries", 3)
        self.rate_limit_delay = self.scraper_config.get("rate_limit_delay", 1.0)

        self.last_request_time = 0

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def _rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _fetch_url(self, url: str, retry_count: int = 0) -> Optional[str]:
        """
        Fetch URL content with retries

        Args:
            url: URL to fetch
            retry_count: Current retry attempt

        Returns:
            HTML content or None on failure
        """
        self._rate_limit()

        try:
            logger.debug(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")

            if retry_count < self.max_retries:
                wait_time = (retry_count + 1) * 2  # Exponential backoff
                logger.info(f"Retrying in {wait_time}s... (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._fetch_url(url, retry_count + 1)

            logger.error(f"Max retries exceeded for {url}")
            return None

    def _parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML content with BeautifulSoup

        Args:
            html: HTML string

        Returns:
            BeautifulSoup object or None on failure
        """
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            return None

    @abstractmethod
    def search(
        self,
        manufacturer: Optional[str] = None,
        material_type: Optional[str] = None,
        material_name: Optional[str] = None,
        color: Optional[str] = None
    ) -> List[ScrapedData]:
        """
        Search for filament data

        Args:
            manufacturer: Manufacturer name
            material_type: Material type (PLA, PETG, etc.)
            material_name: Specific material name
            color: Filament color

        Returns:
            List of ScrapedData objects
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of this data source

        Returns:
            Source name
        """
        pass

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
