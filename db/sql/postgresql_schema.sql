-- ====================================================================
-- Indian Standards (IS) Fire & Building Safety Metadata Database Schema
-- Target: PostgreSQL 14+ with pgvector extension
--
-- DESIGN DISTINCTION:
-- 1. Metadata: IS identity, versions, parts, relationships, keywords, domains.
-- 2. Provenance / Sources: Where the metadata was obtained or verified.
-- 3. Parameters / Embeddings: Prepared schema, unpopulated (no technical content
--    or document bodies manufactured from the metadata TXT).
-- ====================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Domains Table (Normalized domains)
CREATE TABLE IF NOT EXISTS standard_domains (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Core Standards Table (Identity of the IS standard)
CREATE TABLE IF NOT EXISTS standards (
    id BIGSERIAL PRIMARY KEY,
    standard_number VARCHAR(100) NOT NULL UNIQUE, -- e.g. 'IS 2190', 'IS 1644'
    title TEXT NOT NULL,
    domain_id BIGINT REFERENCES standard_domains(id) ON DELETE SET NULL,
    description TEXT,
    committee_designation VARCHAR(255),
    verification_status VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_standards_number ON standards(standard_number);
CREATE INDEX IF NOT EXISTS idx_standards_domain ON standards(domain_id);

-- 4. Standard Versions Table (Year/Edition specific metadata)
CREATE TABLE IF NOT EXISTS standard_versions (
    id BIGSERIAL PRIMARY KEY,
    standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    edition VARCHAR(255),
    status VARCHAR(100),
    revision_description TEXT,
    effective_date DATE,
    verification_status VARCHAR(100),
    notes TEXT,
    bis_standard_id BIGINT UNIQUE,
    extra_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_standard_versions_std_year UNIQUE (standard_id, year)
);

CREATE INDEX IF NOT EXISTS idx_standard_versions_standard ON standard_versions(standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_versions_year ON standard_versions(year);
CREATE INDEX IF NOT EXISTS idx_standard_versions_status ON standard_versions(status);
CREATE INDEX IF NOT EXISTS idx_standard_versions_bis_id ON standard_versions(bis_standard_id);

-- 5. Standard Parts Table (Parts of a standard)
CREATE TABLE IF NOT EXISTS standard_parts (
    id BIGSERIAL PRIMARY KEY,
    standard_version_id BIGINT NOT NULL REFERENCES standard_versions(id) ON DELETE CASCADE,
    part_number VARCHAR(50) NOT NULL,
    part_title TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_standard_parts_version_part UNIQUE (standard_version_id, part_number)
);

CREATE INDEX IF NOT EXISTS idx_standard_parts_version ON standard_parts(standard_version_id);

-- 6. Standard Relationships Table (Revises / supersedes / related-to)
CREATE TABLE IF NOT EXISTS standard_relationships (
    id BIGSERIAL PRIMARY KEY,
    source_standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    source_version_id BIGINT REFERENCES standard_versions(id) ON DELETE SET NULL,
    target_standard_id BIGINT REFERENCES standards(id) ON DELETE SET NULL,
    target_version_id BIGINT REFERENCES standard_versions(id) ON DELETE SET NULL,
    relationship_type VARCHAR(100) NOT NULL CHECK (
        relationship_type IN ('REVISES', 'REVISED_BY', 'SUPERSEDES', 'SUPERSEDED_BY', 'RELATED_TO', 'WITHDRAWN', 'OTHER')
    ),
    target_standard_number_raw VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_standard_relationships UNIQUE (source_version_id, relationship_type, target_standard_number_raw)
);

CREATE INDEX IF NOT EXISTS idx_standard_relationships_source ON standard_relationships(source_standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_relationships_target ON standard_relationships(target_standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_relationships_type ON standard_relationships(relationship_type);

-- 7. Standard Keywords Table & Mapping (Searchable keywords)
CREATE TABLE IF NOT EXISTS standard_keywords (
    id BIGSERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS standard_keyword_map (
    standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    keyword_id BIGINT NOT NULL REFERENCES standard_keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (standard_id, keyword_id)
);

CREATE INDEX IF NOT EXISTS idx_keyword_map_standard ON standard_keyword_map(standard_id);
CREATE INDEX IF NOT EXISTS idx_keyword_map_keyword ON standard_keyword_map(keyword_id);

-- 8. Metadata Provenance & Sources Table (Where metadata was obtained or verified)
CREATE TABLE IF NOT EXISTS standard_sources (
    id BIGSERIAL PRIMARY KEY,
    standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    standard_version_id BIGINT REFERENCES standard_versions(id) ON DELETE SET NULL,
    source_name TEXT,
    source_url TEXT,
    source_type VARCHAR(100),
    provenance_text TEXT NOT NULL, -- Complete verbatim provenance description from source dataset
    verification_status VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_standard_sources UNIQUE (standard_version_id, source_name)
);

CREATE INDEX IF NOT EXISTS idx_standard_sources_std ON standard_sources(standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_sources_ver ON standard_sources(standard_version_id);

-- 9. Standard Technical Parameters Table (Schema ready; unpopulated until technical parameters exist)
CREATE TABLE IF NOT EXISTS standard_parameters (
    id BIGSERIAL PRIMARY KEY,
    standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    standard_version_id BIGINT REFERENCES standard_versions(id) ON DELETE SET NULL,
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value TEXT NOT NULL,
    unit VARCHAR(100),
    description TEXT,
    source_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_standard_params_std ON standard_parameters(standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_params_ver ON standard_parameters(standard_version_id);

-- 10. Standard Embeddings Table (pgvector; schema ready for future vector enrichment)
CREATE TABLE IF NOT EXISTS standard_embeddings (
    id BIGSERIAL PRIMARY KEY,
    standard_id BIGINT NOT NULL REFERENCES standards(id) ON DELETE CASCADE,
    standard_version_id BIGINT REFERENCES standard_versions(id) ON DELETE SET NULL,
    embedding vector(384), -- Configurable embedding dimension
    embedding_model VARCHAR(100),
    text_content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_standard_embeddings_std ON standard_embeddings(standard_id);
CREATE INDEX IF NOT EXISTS idx_standard_embeddings_ver ON standard_embeddings(standard_version_id);
