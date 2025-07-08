from typing import Dict, List, Optional, Tuple
import json
import logging
import os
import asyncio
from google import genai
from urllib.parse import urljoin
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

# Local module imports
from src import config, prompts
from src.scraper_client import ScraperClient
from src.utils import extract_base_url

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup logging and Gemini client
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
geminiClient = genai.Client()

async def extract_links_from_markdown_with_gemini(markdown_content: str, current_page_url: str) -> List[str]:
    """Use Gemini API to extract article links from markdown content."""
    prompt = prompts.get_extract_links_prompt(markdown_content)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL,
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
            resolved_links = [urljoin(current_page_url, link) for link in links]
            return list(set(resolved_links))
        else:
            logger.error(f"Gemini response for links is not a JSON array: {response_text}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini for link extraction: {e}. Response: {response.text[:200]}...")
        return []
    except Exception as e:
        logger.error(f"Error calling Gemini API for link extraction: {e}")
        return []

async def extract_next_page_link_from_markdown_with_gemini(markdown_content: str, current_page_url: str) -> Optional[str]:
    """Use Gemini API to extract the next page link from markdown content."""
    prompt = prompts.get_next_page_prompt(markdown_content)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL,
                contents=prompt
            )
        )
        response_text = response.text.strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text.strip("`").strip()
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()
        if response_text.startswith('"') and response_text.endswith('"'):
            response_text = response_text.strip('"')

        if response_text and response_text.lower() != 'null':
            return urljoin(current_page_url, response_text)
        return None
    except Exception as e:
        logger.error(f"Error calling Gemini API for next page link: {e}")
        return None

async def filter_article_with_gemini(markdown_content: str) -> Optional[Dict[str, str]]:
    """Use Gemini API to filter and translate article content."""
    prompt = prompts.get_filter_article_prompt(markdown_content)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: geminiClient.models.generate_content(
                model=config.API_MODEL,
                contents=prompt
            )
        )
        response_text = response.text.strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text.strip("`").strip()
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

        filtered = json.loads(response_text)
        if isinstance(filtered, dict) and all(k in filtered for k in ["title", "content", "title_english", "content_english"]):
            return filtered
        else:
            logger.error(f"Gemini response JSON does not have expected keys or format: {response_text}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini for article filtering: {e}. Response: {response.text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Error calling Gemini API for article filtering: {e}")
        return None

async def scrape_all_articles(url: str) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """
    Scrape all articles from a starting URL, following pagination.
    """
    async with ScraperClient(url) as scraper:
        results = {}
        page_url = url
        visited_articles = set()
        all_next_page_links = []
        page_num = 1

        while page_url:
            logger.info(f"Scraping page: {page_url}")
            try:
                main_markdown = await scraper.fetch_page(page_url)
            except Exception as e:
                logger.error(f"Could not fetch main page {page_url}: {e}")
                break

            article_links = await extract_links_from_markdown_with_gemini(main_markdown, page_url)
            logger.info(f"Found {len(article_links)} articles on page {page_num}.")

            for article_url in tqdm(article_links, desc=f"Processing articles on page {page_num}"):
                if article_url in visited_articles:
                    continue
                try:
                    logger.info(f"Scraping article: {article_url}")
                    article_markdown = await scraper.fetch_page(article_url)
                    filtered = await filter_article_with_gemini(article_markdown)
                    if filtered:
                        results[article_url] = filtered
                    else:
                        logger.warning(f"Gemini API did not return valid data for {article_url}")
                    visited_articles.add(article_url)
                except Exception as e:
                    logger.error(f"Failed to scrape {article_url}: {e}")

            next_page = await extract_next_page_link_from_markdown_with_gemini(main_markdown, page_url)
            if next_page and next_page != page_url:
                all_next_page_links.append(next_page)
                page_url = next_page
                page_num += 1
            else:
                break

        return results, all_next_page_links