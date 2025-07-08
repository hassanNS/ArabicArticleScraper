def get_extract_links_prompt(markdown_content: str) -> str:
    """Returns the formatted prompt for extracting article links."""
    return (
        "Given the following markdown content of a web page, identify and extract all relevant article links. "
        "These links typically lead to individual articles or lessons. "
        "Return your answer as a JSON array of full URLs. "
        "If a link is relative, resolve it using the current page URL. "
        "Example: ['https://example.com/article1', 'https://example.com/article2']\n\n"
        f"Markdown Content:\n{markdown_content}"
    )

def get_next_page_prompt(markdown_content: str) -> str:
    """Returns the formatted prompt for extracting the next page link."""
    return (
        "Given the following markdown content of a web page, identify and extract the URL for the 'next page' in a pagination sequence. "
        "Return only the full URL as a string. If no next page link is found, return an empty string or null. "
        "If the link is relative, resolve it using the current page URL. "
        "Example: 'https://example.com/page/1', 'https://example.com/page/next'"
        "Wrong Examples: 'https://example.com/page/', 'https://example.com/level/'"
        f"Markdown Content:\n{markdown_content}"
    )

def get_filter_article_prompt(markdown_content: str) -> str:
    """Returns the formatted prompt for filtering and translating article content."""
    return (
        "Given the following markdown content of an article, "
        "extract only the article title and the main article content. "
        "Translate the article title to English. "
        "Also provide the English translation of the main article content. "
        "**Ensure all Arabic text in 'title' and 'content' includes appropriate tashkeel (diacritics).** "
        "Return your answer as a JSON object with keys 'title', 'title_english', 'content', and 'content_english'.\n\n"
        f"Markdown Content:\n{markdown_content}"
    )