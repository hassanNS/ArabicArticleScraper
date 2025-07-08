import aiohttp
import asyncio
import logging
from typing import Optional
from src import config

logger = logging.getLogger(__name__)

class ScraperClient:
    """
    A class for scraping web content via Jina AI's reader endpoint.
    It manages an aiohttp session for making asynchronous HTTP requests.
    """

    def __init__(self, base_url: str):
        """
        Initialize the scraper with a base URL.
        """
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Initializes the aiohttp session."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the aiohttp session."""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> str:
        """
        Fetch the markdown content of a page via Jina AI.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        jina_url = f"{config.JINA_AI_PREFIX}{url}"
        logger.info(f"Fetching via Jina AI: {jina_url}")

        try:
            async with self.session.get(jina_url, timeout=90) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {jina_url}: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {jina_url}")
            raise