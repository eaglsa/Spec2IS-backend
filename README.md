# Spec2IS — Indian Standards (IS) Recommendation Engine Backend

Prototype API for SIH 2026 PS 26108.
Given an engineering specification text, Spec2IS extracts requirements and retrieves relevant Indian Standards (IS) using hybrid keyword + vector search, status validation, and LLM-powered context explanations.

---

## Directory Structure

```
Spec2IS-backend/
├── db/
│   ├── models.py                  # SQLAlchemy ORM models (Tier 1-3 normalized schema)
│   ├── session.py                 # Async engine & FastAPI session dependency
│   └── sql/
│       ├── schema.sql             # PostgreSQL + pgvector schema definition
│       ├── seed_data.sql          # Seed data generated from metadata extraction
│       └── validation_queries.sql # DB verification & audit SQL queries
├── pipeline/
│   ├── extract.py                 # Step 1: LLM requirement extraction
│   ├── retrieve.py                # Steps 2-4: Keyword & pgvector hybrid search
│   ├── validate.py                # Step 5: Deterministic revision & part status checks
│   └── explain.py                 # Step 6: LLM justification generation
├── scripts/
│   └── import_standards.py        # Import pipeline script (TXT -> SQL generator)
├── data/
│   └── IS_fire_building_safety_metadata_extracted.txt  # Raw metadata source
├── llm_client.py                  # Multi-provider LLM client (Gemini / Anthropic)
├── main.py                        # FastAPI application entry point
├── schemas.py                     # Pydantic v2 API request/response models
├── requirements.txt               # Python package dependencies
├── .env.example                   # Environment configuration template
└── README.md                      # Project documentation
```

---

## Quick Start

### 1. Installation

Create a virtual environment and install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup

1. Enable the `vector` extension in PostgreSQL 14+:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Initialize the schema:
```bash
psql -U postgres -d spec2is -f db/sql/schema.sql
```

3. Load seed metadata:
```bash
psql -U postgres -d spec2is -f db/sql/seed_data.sql
```

*(Optional)* Re-generate seed SQL from metadata TXT:
```bash
python scripts/import_standards.py
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and set your database connection string and LLM API keys:

```ini
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/spec2is
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Running the API

Start the FastAPI application:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### `POST /analyze`

Analyzes an engineering specification string and returns ranked IS standard recommendations.

**Request Body:**
```json
{
  "specification_text": "Building fire safety requirements including portable CO2 fire extinguishers, exit signage, and sprinkler system operating pressure of 2.5 bar."
}
```

**Response:**
```json
{
  "specification": "...",
  "recommendations": [
    {
      "standard_number": "IS 2190",
      "version_year": "2010",
      "status": "current",
      "confidence": 0.892,
      "action": "recommended",
      "why": "IS 2190 specifies selection, installation, and maintenance of first-aid fire extinguishers.",
      "replacement_standard": null,
      "ambiguous": false,
      "ambiguity_reason": null
    }
  ],
  "areas_to_verify": []
}
```