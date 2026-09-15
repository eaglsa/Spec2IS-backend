# PostgreSQL Setup & Initialization for Spec2IS

This document provides the standard operating procedure for deploying the Spec2IS database on a live PostgreSQL server (e.g., local bare-metal, Docker, Supabase, RDS, Neon).

## 1. Prerequisites
- **PostgreSQL Version:** 14+
- **Required Extension:** `pgvector`
- **Source Database:** `sqlite:///bis_extractor/output/bis_standards.db` (Contains ~14,387 crawler records)

## 2. Environment Configuration
Create or update your `.env` file with your target credentials:
```env
# The ETL will only execute if this is explicitly a postgresql URL
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR_PASSWORD]@[HOST]:5432/spec2is_db

# The immutable crawler source database
CRAWLER_DATABASE_URL=sqlite:///bis_extractor/output/bis_standards.db
```

## 3. Database & User Creation
Before initializing the schema, connect to your PostgreSQL server as a superuser (e.g., `postgres`) and run the creation script:
```bash
psql -U postgres -h [HOST] -f db/sql/create_database.sql
```
*Note: `create_database.sql` creates the `spec2is_db` database and enables the `vector` extension.*

## 4. Schema Initialization
Once the database exists, execute the schema definition against it:
```bash
psql -U postgres -h [HOST] -d spec2is_db -f db/sql/postgresql_schema.sql
```

## 5. Verify the Schema
Run the schema validation queries to ensure `JSONB` and `vector` are correctly applied:
```bash
psql -U postgres -h [HOST] -d spec2is_db -f db/sql/validation.sql
```

## 6. Run the ETL Pipeline
The ETL pipeline transfers the flat crawler records into the normalized Spec2IS architecture. It will abort if it detects it is not targeting a PostgreSQL instance.

**Dry Run:**
```bash
python scripts/import_from_crawler.py --dry-run
```

**Full Production Import:**
```bash
python scripts/import_from_crawler.py
```

## 7. Post-Import Validation
After the import finishes, re-run the validation queries to verify that cardinality rules were followed (e.g. multiple editions grouped under one Enduring Standard identity) and that `bis_standard_id` was uniformly mapped:
```bash
psql -U postgres -h [HOST] -d spec2is_db -f db/sql/validation.sql
```

## 8. Generate Incremental Embeddings
The embedding generator respects existing vectors and only processes new or updated records:
```bash
python scripts/generate_embeddings.py
```
