# Spec2IS-backend: Indian Standards Metadata & Provenance Relational Engine

A normalized PostgreSQL relational database schema and idempotent data pipeline for Indian Standards (IS) metadata related to fire safety, building safety, and technical compliance.

## Architecture & Design Principles

1. **Metadata vs. Provenance Distinction**:
   - standards, standard_versions, standard_parts, standard_relationships, standard_domains, standard_keywords: Store normalized metadata of IS documents.
   - standard_sources: Stores provenance audit records (where/how metadata was verified, original source text, URLs, verification status, and data conflicts).
2. **Prepared Enrichment Schemas**:
   - standard_parameters: Schema ready for technical parameter values (unpopulated until granular datasets are ingested).
   - standard_embeddings: Schema ready with pgvector for semantic search / vector similarity matching.
3. **Strict Source Faithfulness**:
   - No manufactured parameters, fake clause text, or synthetic embeddings.
   - Conflicting records between sources are faithfully preserved in 
otes rather than silently resolved.
   - Idempotent upserts (ON CONFLICT) across all tables.

## Quickstart

### 1. Apply Schema
`ash
psql -h <host> -U <user> -d <database> -f schema.sql
`

### 2. Apply Seed Data
`ash
psql -h <host> -U <user> -d <database> -f seed_data.sql
`

### 3. Or Run the Python Pipeline
`ash
python import_standards.py --input IS_fire_building_safety_metadata_extracted.txt --output seed_data.sql
`

### 4. Run Validation Queries
`ash
psql -h <host> -U <user> -d <database> -f validation_queries.sql
`
