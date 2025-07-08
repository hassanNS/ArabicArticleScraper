import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import json

from src.scraper import (
    ArabicScraper,
    extract_links_from_markdown_with_gemini,
    extract_next_page_link_from_markdown_with_gemini,
    filter_article_with_gemini,
    scrape_all_articles
)

# Mock data
MOCK_MARKDOWN = """
# Main Page

[Article 1](https://example.com/article1)
[Article 2](/article2)
[Next Page](https://example.com/page/2)
"""

MOCK_ARTICLE_MARKDOWN = "# Article Title\nContent here."

MOCK_LINKS_RESPONSE = json.dumps([
    "https://example.com/article1",
    "/article2"
])

MOCK_NEXT_PAGE_RESPONSE = "https://example.com/page/2"

MOCK_FILTERED_ARTICLE_RESPONSE = json.dumps({
    "title": "عنوان",
    "title_english": "Title",
    "content": "محتوى",
    "content_english": "Content"
})

class TestScraper(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    @patch('src.scraper.aiohttp.ClientSession')
    def test_fetch_page(self, MockSession):
        mock_response_text = "MOCKED PAGE"

        # This mock will be the 'response' object inside the async with block
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status.return_value = None
        mock_response_obj.text.return_value = mock_response_text

        # Create a MagicMock that will act as the async context manager
        # returned by session.get(). It needs __aenter__ and __aexit__.
        mock_async_context_manager = MagicMock()
        mock_async_context_manager.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_async_context_manager.__aexit__ = AsyncMock(return_value=None)

        # Create the mock for the ClientSession instance
        mock_session_instance = AsyncMock()
        # When .get() is called on the session instance, it should return our async context manager mock
        mock_session_instance.get = MagicMock(return_value=mock_async_context_manager)

        # When aiohttp.ClientSession() is called, it should return our mocked session instance
        MockSession.return_value = mock_session_instance

        async def run():
            async with ArabicScraper("http://test.com") as scraper:
                result = await scraper.fetch_page("http://test.com/page")
                self.assertEqual(result, mock_response_text)
        self.loop.run_until_complete(run())

    @patch('src.scraper.geminiClient.models.generate_content')
    def test_extract_links_from_markdown_with_gemini(self, mock_gemini):
        mock_resp = MagicMock()
        mock_resp.text = MOCK_LINKS_RESPONSE
        mock_gemini.return_value = mock_resp

        async def run():
            links = await extract_links_from_markdown_with_gemini(MOCK_MARKDOWN, "https://example.com/main")
            self.assertIn("https://example.com/article1", links)
            self.assertIn("https://example.com/article2", links)
        self.loop.run_until_complete(run())

    @patch('src.scraper.geminiClient.models.generate_content')
    def test_extract_next_page_link_from_markdown_with_gemini(self, mock_gemini):
        mock_resp = MagicMock()
        mock_resp.text = MOCK_NEXT_PAGE_RESPONSE
        mock_gemini.return_value = mock_resp

        async def run():
            next_link = await extract_next_page_link_from_markdown_with_gemini(MOCK_MARKDOWN, "https://example.com/main")
            self.assertEqual(next_link, "https://example.com/page/2")
        self.loop.run_until_complete(run())

    @patch('src.scraper.geminiClient.models.generate_content')
    def test_filter_article_with_gemini(self, mock_gemini):
        mock_resp = MagicMock()
        mock_resp.text = MOCK_FILTERED_ARTICLE_RESPONSE
        mock_gemini.return_value = mock_resp

        async def run():
            filtered = await filter_article_with_gemini(MOCK_ARTICLE_MARKDOWN)
            self.assertEqual(filtered["title_english"], "Title")
            self.assertEqual(filtered["content_english"], "Content")
        self.loop.run_until_complete(run())

    @patch('src.scraper.filter_article_with_gemini')
    @patch('src.scraper.extract_next_page_link_from_markdown_with_gemini')
    @patch('src.scraper.extract_links_from_markdown_with_gemini')
    @patch('src.scraper.ArabicScraper.fetch_page')
    def test_scrape_all_articles(self, mock_fetch_page, mock_extract_links, mock_extract_next, mock_filter_article):
        # Setup mocks
        mock_fetch_page.side_effect = [
            MOCK_MARKDOWN,  # main page
            MOCK_ARTICLE_MARKDOWN,  # article 1
            MOCK_ARTICLE_MARKDOWN   # article 2
        ]
        mock_extract_links.return_value = [
            "https://example.com/article1",
            "https://example.com/article2"
        ]
        mock_extract_next.side_effect = [
            "https://example.com/page/2",  # first call
            None  # second call
        ]
        mock_filter_article.return_value = json.loads(MOCK_FILTERED_ARTICLE_RESPONSE)

        async def run():
            articles, next_pages = await scrape_all_articles("https://example.com/main")
            self.assertEqual(len(articles), 2)
            self.assertIn("https://example.com/article1", articles)
            self.assertIn("https://example.com/article2", articles)
            self.assertEqual(next_pages, ["https://example.com/page/2"])
        self.loop.run_until_complete(run())
