import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///output/bis_standards.db")
CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "5"))
CRAWL_DELAY_SECONDS = float(os.getenv("CRAWL_DELAY_SECONDS", "1.0"))
RETRY_LIMIT = int(os.getenv("RETRY_LIMIT", "3"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))

OUTPUT_DIR = BASE_DIR / "output"
RAW_STORAGE_DIR = OUTPUT_DIR / "raw"
DOCUMENTS_DIR = OUTPUT_DIR / "documents"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they do not exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
