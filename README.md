# ArabicScraper

A Python project for web scraping Arabic content.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Project

```bash
python src/main.py "<url_to_scrape>"
```

## Running the Project with Dummy Data
```
python src/main.py --dummy-data
```

## Running Tests

```bash
pytest tests/
```
