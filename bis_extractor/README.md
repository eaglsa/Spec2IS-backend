# BIS Standards Extractor

A robust, resumable data extraction system for the Bureau of Indian Standards (BIS) website.

## Features
- Modular crawler with Playwright and httpx.
- SQLAlchemy for relational state and data storage (resumability).
- Raw data preservation for all API calls/HTML pages.
- PDF extraction with PyMuPDF and pdfplumber.
- CLI interface for discovery, crawling, validation, and export.

## Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install --with-deps chromium
   ```
2. Copy configuration:
   ```bash
   cp .env.example .env
   ```
   
## Usage
```bash
python main.py discover
python main.py crawl
python main.py validate
```
