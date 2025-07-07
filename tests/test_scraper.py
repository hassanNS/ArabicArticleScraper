"""
Test cases for the Arabic scraper module.
"""
import pytest
from bs4 import BeautifulSoup
from src.scraper import ArabicScraper

@pytest.mark.asyncio
async def test_extract_text():
    """Test extracting Arabic text from HTML content."""
    html = """
    <html>
        <body>
            <p>مرحبا بالعالم</p>
            <p>Hello World</p>
            <p>السلام عليكم</p>
        </body>
    </html>
    """

    async with ArabicScraper("http://example.com") as scraper:
        text_segments = await scraper.extract_text(html)
        assert len(text_segments) == 2
        assert "مرحبا بالعالم" in text_segments
        assert "السلام عليكم" in text_segments
        assert "Hello World" not in text_segments
