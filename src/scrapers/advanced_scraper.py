"""
Advanced web scraping with anti-detection techniques
"""

import time
import random
import hashlib
import json
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.data.models import ScrapedData
from src.utils.logger import get_logger

logger = get_logger()


class AdvancedScraper:
    """
    Advanced scraper with anti-detection features:
    - User-agent rotation
    - Smart caching
    - Exponential backoff with jitter
    - Session persistence
    - Header randomization
    """

    # Realistic user agents from various browsers
    USER_AGENTS = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',

        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',

        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',

        # Chrome on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

        # Safari on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',

        # Chrome on Linux
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    # Common accept languages
    ACCEPT_LANGUAGES = [
        'en-US,en;q=0.9',
        'en-GB,en;q=0.9',
        'en-US,en;q=0.9,es;q=0.8',
    ]

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize advanced scraper

        Args:
            cache_dir: Directory for caching responses
        """
        self.session = requests.Session()
        self.last_request_time = {}  # Per-domain tracking

        # Set up caching
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.min_delay = 2.0  # Minimum delay between requests (seconds)
        self.max_delay = 5.0  # Maximum delay
        self.cache_ttl = 24 * 60 * 60  # 24 hours in seconds
        self.max_retries = 5

        logger.info("Advanced scraper initialized with caching and anti-detection")

    def _get_random_headers(self) -> Dict[str, str]:
        """
        Generate randomized but realistic headers

        Returns:
            Dictionary of HTTP headers
        """
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(self.ACCEPT_LANGUAGES),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting"""
        from urllib.parse import urlparse
        return urlparse(url).netloc

    def _rate_limit(self, domain: str):
        """
        Apply smart rate limiting per domain with random jitter

        Args:
            domain: Domain to rate limit
        """
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            # Random delay between min and max
            required_delay = random.uniform(self.min_delay, self.max_delay)

            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.time()

        self.last_request_time[domain] = time.time()

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cached(self, url: str) -> Optional[str]:
        """
        Get cached response if available and not expired

        Args:
            url: URL to check cache for

        Returns:
            Cached content or None
        """
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # Check if expired
            cached_time = datetime.fromisoformat(cached['timestamp'])
            age = (datetime.now() - cached_time).total_seconds()

            if age < self.cache_ttl:
                logger.debug(f"Cache hit for {url} (age: {age:.0f}s)")
                return cached['content']
            else:
                logger.debug(f"Cache expired for {url}")
                cache_file.unlink()  # Delete expired cache
                return None

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def _cache_response(self, url: str, content: str):
        """
        Cache response to disk

        Args:
            url: URL that was fetched
            content: Response content
        """
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cached_data = {
                'url': url,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f)

            logger.debug(f"Cached response for {url}")

        except Exception as e:
            logger.error(f"Error caching response: {e}")

    def fetch_url(
        self,
        url: str,
        use_cache: bool = True,
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Fetch URL with advanced anti-detection

        Args:
            url: URL to fetch
            use_cache: Whether to use cache
            retry_count: Current retry attempt

        Returns:
            HTML content or None
        """
        # Try cache first
        if use_cache:
            cached = self._get_cached(url)
            if cached:
                return cached

        # Rate limit per domain
        domain = self._get_domain(url)
        self._rate_limit(domain)

        # Set random headers
        headers = self._get_random_headers()

        try:
            logger.debug(f"Fetching: {url}")

            response = self.session.get(
                url,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    # Exponential backoff with jitter
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    logger.warning(f"Rate limited (429). Waiting {wait_time:.1f}s before retry {retry_count + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    return self.fetch_url(url, use_cache=False, retry_count=retry_count + 1)
                else:
                    logger.error(f"Max retries exceeded for {url}")
                    return None

            response.raise_for_status()

            # Cache successful response
            if use_cache:
                self._cache_response(url, response.text)

            return response.text

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")

            if retry_count < self.max_retries:
                # Exponential backoff
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.info(f"Retrying in {wait_time:.1f}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self.fetch_url(url, use_cache=use_cache, retry_count=retry_count + 1)

            logger.error(f"Max retries exceeded for {url}")
            return None

    def clear_cache(self, older_than_hours: Optional[int] = None):
        """
        Clear cache files

        Args:
            older_than_hours: Only clear cache older than this many hours (None = all)
        """
        count = 0
        cutoff_time = None

        if older_than_hours is not None:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cutoff_time:
                    # Check file age
                    with open(cache_file, 'r') as f:
                        cached = json.load(f)
                    cached_time = datetime.fromisoformat(cached['timestamp'])

                    if cached_time < cutoff_time:
                        cache_file.unlink()
                        count += 1
                else:
                    cache_file.unlink()
                    count += 1

            except Exception as e:
                logger.error(f"Error clearing cache file {cache_file}: {e}")

        logger.info(f"Cleared {count} cache files")

    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML with BeautifulSoup

        Args:
            html: HTML string

        Returns:
            BeautifulSoup object or None
        """
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            return None
