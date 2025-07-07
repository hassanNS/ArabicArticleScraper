from typing import Dict, List, Optional
import aiohttp
import json
import logging
from bs4 import BeautifulSoup
import os
from google import genai
import asyncio
from utils import extract_base_url
from urllib.parse import urljoin

GEMINI_API_KEY = "AIzaSyCV_cf8q-9BKY-19u-eb6zSKA9Wdq3_m7Q"
API_MODEL = "gemini-1.5-pro"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
geminiClient = genai.Client()

class ArabicScraper:
    """
    A class for scraping Arabic content from Al Jazeera lessons pages.
    """

    def __init__(self, base_url: str):
        """
        Initialize the scraper with a base URL.
        """
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> str:
        """
        Fetch the HTML content of a page.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    async def extract_text(self, html: str) -> List[str]:
        """
        Extract Arabic text segments from HTML.
        """
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text_segments = []
        for text in soup.stripped_strings:
            if any('\u0600' <= char <= '\u06FF' for char in text):
                text_segments.append(text.strip())
        return text_segments

    async def extract_links_in_section(self, html: str, section_selector: str, base_url: Optional[str] = None) -> List[str]:
      """
      Extract all links (full URLs) within a given section specified by a CSS selector.

      Args:
        html (str): The HTML content to parse.
        section_selector (str): CSS selector for the section to search within.
        base_url (Optional[str]): Base URL to resolve relative links. If not provided, relative links are skipped.

      Returns:
        List[str]: List of full URLs found in the section.
      """
      soup = BeautifulSoup(html, 'html.parser')
      links = []
      section = soup.select_one(section_selector)
      if not section:
        return []
      for a in section.find_all('a', href=True):
        href = a['href']
        if href.startswith('http'):
          links.append(href)
        elif base_url:
          links.append(urljoin(base_url, href))
      return list(set(links))

    async def extract_next_page_link(self, html: str, next_page_selector:str, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract the next page link from the pagination section.
        """
        soup = BeautifulSoup(html, 'html.parser')
        next_link = soup.select_one(next_page_selector)
        if next_link and next_link.get('href'):
            href = next_link['href']
            if href.startswith('http'):
                return href
            else:
                return base_url + href
        return None

async def filter_article_with_gemini(text_segments: List[str]) -> Optional[Dict[str, str]]:
    """
    Use Gemini API to extract the article title and content from the scraped text.

    Args:
        text_segments (List[str]): List of text segments from the article.

    Returns:
        Optional[Dict[str, str]]: Dictionary with 'title' and 'content', or None on failure.
    """
    prompt = (
        "Given the following list of text segments from a web page, "
        "extract only the article title and the main article content. Translate the article title to English"
        "Return your answer as a JSON object with keys 'title', 'title_english' and 'content'.\n\n"
        f"Segments: {json.dumps(text_segments, ensure_ascii=False)}"
    )

    # google-genai is synchronous, so run in a thread to avoid blocking
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=API_MODEL,
                contents=prompt
            )
        )

        response_text = response.text.strip()

        # Remove code block markers if present
        if response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text.strip("`").strip()
        # Try to find JSON inside code block
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

        filtered = json.loads(response_text)
        if isinstance(filtered, dict) and "title" in filtered and "content" in filtered:
            return filtered
        else:
            logger.error("Gemini response JSON does not have expected keys.")
            return None
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None

async def scrape_all_articles(url: str) -> Dict[str, Dict[str, str]]:
    """
    Scrape all articles from the main lessons page, following pagination,
    and filter each article using Gemini API.

    Args:
        url (str): The URL of the main lessons page.

    Returns:
        Dict[str, Dict[str, str]]: Dictionary mapping article URLs to dicts with 'title' and 'content'.
    """
    async with ArabicScraper(url) as scraper:
        results = {}
        page_url = url
        base_url = extract_base_url(page_url)
        visited_articles = set()
        page_num = 1

        while page_url:
            logger.info(f"Scraping page: {page_url}")
            main_html = await scraper.fetch_page(page_url)
            article_links = await scraper.extract_links_in_section(main_html, ".views-view-grid", base_url)
            logger.info(f"Found {len(article_links)} articles on page {page_num}.")

            for article_url in article_links:
                if article_url in visited_articles:
                    continue
                try:
                    logger.info(f"Scraping article: {article_url}")
                    article_html = await scraper.fetch_page(article_url)
                    text_segments = await scraper.extract_text(article_html)
                    filtered = await filter_article_with_gemini(text_segments)
                    if filtered:
                        results[article_url] = filtered
                    else:
                        logger.warning(f"Gemini API did not return valid data for {article_url}")
                    visited_articles.add(article_url)
                except Exception as e:
                    logger.error(f"Failed to scrape {article_url}: {e}")

            next_page = await scraper.extract_next_page_link(main_html, "li.pager__item", base_url)#(main_html, "li.pager__item--next a", base_url)
            if next_page and next_page != page_url:
                page_url = next_page
                page_num += 1
            else:
                break

        return results
