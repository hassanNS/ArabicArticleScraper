import asyncio
from scraper import scrape_all_articles
from pdf_generator import generate_pdf
import os

async def main() -> None:
    """
    Scrape all articles from a list of URLs and generate a PDF with the content.
    """
    urls = [
        "https://learning.aljazeera.net/en/lessons/level/elementary"
    ]

    # Create tasks for scraping
    tasks = [scrape_all_articles(url) for url in urls]
    list_of_results = await asyncio.gather(*tasks)

    # Combine results
    all_articles = {}
    for result_dict in list_of_results:
        all_articles.update(result_dict)

    # Check if we have any articles before generating PDF
    if not all_articles:
        print("Error: No articles were found to generate the PDF.")
        return

    # Generate PDF
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, 'arabic_lessons.pdf')

    generate_pdf(all_articles, pdf_path)
    print(f"PDF generated successfully at: {pdf_path}")

if __name__ == "__main__":
    asyncio.run(main())