from typing import Dict, List, Optional, Tuple
import aiohttp
import json
import logging
from bs4 import BeautifulSoup
import os
from google import genai
import asyncio
from src.utils import extract_base_url # Changed to absolute import
from urllib.parse import urljoin
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
from src import config # This remains correct

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure API key is available before initializing geminiClient
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file or environment variables.")

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
        Fetch the markdown content of a page via Jina AI.
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")
        jina_url = f"{config.JINA_AI_PREFIX}{url}" # Use JINA_AI_PREFIX from config
        logger.info(f"Fetching via Jina AI: {jina_url}")
        try:
            async with self.session.get(jina_url, timeout=30) as response: # Added timeout
                response.raise_for_status() # Raise an exception for bad status codes
                return await response.text() # This will be markdown
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {jina_url}: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {jina_url}")
            raise

async def extract_links_from_markdown_with_gemini(markdown_content: str, current_page_url: str) -> List[str]:
    """
    Use Gemini API to extract article links from markdown content.
    """
    prompt = (
        "Given the following markdown content of a web page, identify and extract all relevant article links. "
        "These links typically lead to individual articles or lessons. "
        "Return your answer as a JSON array of full URLs. "
        "If a link is relative, resolve it using the current page URL. "
        "Example: ['https://example.com/article1', 'https://example.com/article2']\n\n"
        f"Markdown Content:\n{markdown_content}"
    )
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL, # Use API_MODEL from config
                contents=prompt
            )
        )
        response_text = response.text.strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text.strip("`").strip()
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

        links = json.loads(response_text)
        if isinstance(links, list):
            # Resolve relative URLs if Gemini returns them
            resolved_links = [urljoin(current_page_url, link) for link in links]
            return list(set(resolved_links)) # Use set to remove duplicates
        else:
            logger.error(f"Gemini response for links is not a JSON array: {response_text}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini for link extraction: {e}. Response: {response_text[:200]}...")
        return []
    except Exception as e:
        logger.error(f"Error calling Gemini API for link extraction: {e}")
        return []

async def extract_next_page_link_from_markdown_with_gemini(markdown_content: str, current_page_url: str) -> Optional[str]:
    """
    Use Gemini API to extract the next page link from markdown content.
    """
    prompt = (
        "Given the following markdown content of a web page, identify and extract the URL for the 'next page' in a pagination sequence. "
        "Return only the full URL as a string. If no next page link is found, return an empty string or null. "
        "If the link is relative, resolve it using the current page URL. "
        "Example: 'https://example.com/page/2'\n\n"
        f"Markdown Content:\n{markdown_content}"
    )
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL, # Use API_MODEL from config
                contents=prompt
            )
        )
        response_text = response.text.strip()
        # Clean up response (Gemini might wrap in quotes or code blocks)
        if response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text.strip("`").strip()
        if response_text.startswith("json"): # Sometimes it might return "json\n"
            response_text = response_text[4:].strip()
        if response_text.startswith('"') and response_text.endswith('"'): # If it returns a string in quotes
            response_text = response_text.strip('"')

        if response_text and response_text.lower() != 'null':
            return urljoin(current_page_url, response_text)
        return None
    except Exception as e:
        logger.error(f"Error calling Gemini API for next page link: {e}")
        return None

async def filter_article_with_gemini(markdown_content: str) -> Optional[Dict[str, str]]:
    """
    Use Gemini API to extract the article title, content, and their English translations from markdown.

    Args:
        markdown_content (str): Markdown content of the article.

    Returns:
        Optional[Dict[str, str]]: Dictionary with 'title', 'title_english', 'content', and 'content_english', or None on failure.
    """
    prompt = (
        "Given the following markdown content of an article, "
        "extract only the article title and the main article content. "
        "Translate the article title to English. "
        "Also provide the English translation of the main article content. "
        "**Ensure all Arabic text in 'title' and 'content' includes appropriate tashkeel (diacritics).** "
        "Return your answer as a JSON object with keys 'title', 'title_english', 'content', and 'content_english'.\n\n"
        f"Markdown Content:\n{markdown_content}"
    )

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL, # Use API_MODEL from config
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
        if isinstance(filtered, dict) and "title" in filtered and "content" in filtered and "title_english" in filtered and "content_english" in filtered:
            return filtered
        else:
            logger.error(f"Gemini response JSON does not have expected keys or format: {response_text}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini for article filtering: {e}. Response: {response_text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Error calling Gemini API for article filtering: {e}")
        return None

async def scrape_all_articles(url: str) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """
    Scrape all articles from the main lessons page, following pagination,
    and filter each article using Gemini API.

    Args:
        url (str): The URL of the main lessons page.

    Returns:
        Tuple[Dict[str, Dict[str, str]], List[str]]: Dictionary mapping article URLs to dicts with
        'title', 'title_english', 'content', 'content_english', and a list of all next page links encountered.
    """
    async with ArabicScraper(url) as scraper:
        results = {}
        page_url = url
        base_url = extract_base_url(page_url)
        visited_articles = set()
        all_next_page_links = []
        page_num = 1

        while page_url:
            logger.info(f"Scraping page: {page_url}")
            try:
                main_markdown = await scraper.fetch_page(page_url) # Fetch markdown via Jina AI
            except Exception as e:
                logger.error(f"Could not fetch main page {page_url}: {e}")
                break # Stop if main page cannot be fetched

            # Extract article links from markdown using Gemini
            article_links = await extract_links_from_markdown_with_gemini(main_markdown, page_url)
            logger.info(f"Found {len(article_links)} articles on page {page_num}.")

            # Use tqdm for progress bar over articles
            for article_url in tqdm(article_links, desc=f"Processing articles on page {page_num}"):
                if article_url in visited_articles:
                    continue
                try:
                    logger.info(f"Scraping article: {article_url}")
                    article_markdown = await scraper.fetch_page(article_url) # Fetch article markdown via Jina AI
                    filtered = await filter_article_with_gemini(article_markdown)
                    if filtered:
                        results[article_url] = filtered
                    else:
                        logger.warning(f"Gemini API did not return valid data for {article_url}")
                    visited_articles.add(article_url)
                except Exception as e:
                    logger.error(f"Failed to scrape {article_url}: {e}")

            # Extract next page link from markdown using Gemini
            next_page = await extract_next_page_link_from_markdown_with_gemini(main_markdown, page_url)
            if next_page and next_page != page_url:
                all_next_page_links.append(next_page) # Collect all next page links
                page_url = next_page
                page_num += 1
            else:
                break

        return results, all_next_page_links
