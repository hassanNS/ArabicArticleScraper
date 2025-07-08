import asyncio
import os
import argparse
from typing import Dict, List, Tuple
import sys
from tqdm.asyncio import tqdm # Import tqdm.asyncio for async progress bars

# Add the project root to sys.path to allow imports from sibling directories like 'tests'
# This line is crucial for absolute imports to work when main.py is run directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scraper import scrape_all_articles # Changed to absolute import
from src.pdf_generator import generate_pdf # Changed to absolute import
from src import config # This remains correct

async def main() -> None:
    """
    Scrape all articles from a list of URLs and generate a PDF with the content.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Scrape Arabic articles and generate a PDF.")
    parser.add_argument("url", type=str, nargs='?', default=None, help="The starting URL to scrape (e.g., 'https://learning.aljazeera.net/en/lessons/level/elementary')")
    parser.add_argument("--dummy-data", action="store_true", help="Use dummy data for PDF generation instead of scraping.")
    args = parser.parse_args()

    all_articles: Dict[str, Dict[str, str]] = {}
    all_next_page_links: List[str] = []

    if args.dummy_data:
        print("Using dummy data for PDF generation.")
        from tests.data.dummy_articles import DUMMY_ARTICLES
        all_articles = DUMMY_ARTICLES
        # Dummy data doesn't involve next page links, so this list remains empty
    else:
        if not args.url:
            print("Error: URL is required unless --dummy-data is used.")
            parser.print_help()
            return

        urls = [args.url]

        # Create tasks for scraping
        # Use tqdm.asyncio.gather for a progress bar over multiple URLs if needed
        tasks = [scrape_all_articles(url) for url in urls]
        list_of_results_and_links: List[Tuple[Dict[str, Dict[str, str]], List[str]]] = await tqdm.gather(*tasks, desc="Scraping URLs")

        # Combine results and collect all next page links
        for articles_dict, next_page_links in list_of_results_and_links:
            all_articles.update(articles_dict)
            all_next_page_links.extend(next_page_links)

    # Check if we have any articles before generating PDF
    if not all_articles:
        print("Error: No articles were found to generate the PDF.")
        return

    # Generate PDF
    os.makedirs(config.OUTPUT_DIR, exist_ok=True) # Use OUTPUT_DIR from config
    pdf_path = os.path.join(config.OUTPUT_DIR, 'arabic_lessons.pdf')

    print(f"Generating PDF with {len(all_articles)} articles...")
    generate_pdf(all_articles, pdf_path)
    print(f"PDF generated successfully at: {pdf_path}")

    # Print the next page links (only if not using dummy data)
    if not args.dummy_data and all_next_page_links:
        print("\nDiscovered Next Page Links:")
        for link in sorted(list(set(all_next_page_links))): # Print unique links
            print(f"- {link}")
    elif not args.dummy_data:
        print("\nNo additional next page links were discovered.")

if __name__ == "__main__":
    asyncio.run(main())