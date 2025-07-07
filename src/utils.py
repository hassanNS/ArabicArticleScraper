from urllib.parse import urlparse

def extract_base_url(full_url: str) -> str:
    """
    Extract the base URL from a full URL.

    Args:
        full_url (str): The complete URL.

    Returns:
        str: The base URL (scheme + netloc).
    """
    parsed_url = urlparse(full_url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"