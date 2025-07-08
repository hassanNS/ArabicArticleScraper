import os

# --- API Settings ---
API_MODEL = "gemini-1.5-pro" # Gemini API model to use

# --- Paths ---
# Base directory of the project (one level up from src)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Output directory for PDFs
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Fonts directory
FONTS_DIR = os.path.join(BASE_DIR, 'fonts')

# --- Scraping Settings ---
JINA_AI_PREFIX = "https://r.jina.ai/"