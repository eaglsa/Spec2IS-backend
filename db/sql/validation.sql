-- ====================================================================
-- Spec2IS PostgreSQL & ETL Validation Queries
-- ====================================================================

-- --------------------------------------------------------------------
-- PART 1: SCHEMA VALIDATION
-- --------------------------------------------------------------------

-- 1. Check pgvector extension
SELECT extname, extversion 
FROM pg_extension 
WHERE extname = 'vector';

-- 2. Verify JSONB and BIGINT on standard_versions
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'standard_versions' 
AND column_name IN ('bis_standard_id', 'extra_metadata');

-- 3. Verify Unique Constraint on bis_standard_id
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'standard_versions' 
AND indexname LIKE '%bis%';

-- --------------------------------------------------------------------
-- PART 2: POST-IMPORT VALIDATION
-- --------------------------------------------------------------------

-- 1. Count Crawler Source Records vs Targets
-- (Manual check against the ETL output which should report ~14387)
SELECT COUNT(*) as total_standard_versions FROM standard_versions;
SELECT COUNT(*) as total_standards FROM standards;

-- 2. Check for Duplicate BIS IDs (Must be 0)
SELECT bis_standard_id, COUNT(*)
FROM standard_versions
WHERE bis_standard_id IS NOT NULL
GROUP BY bis_standard_id
HAVING COUNT(*) > 1;

-- 3. Count NULL bis_standard_id (Should be 0 if all imported strictly via ETL)
SELECT COUNT(*) as missing_bis_id FROM standard_versions WHERE bis_standard_id IS NULL;

-- 4. Verify Standard vs StandardVersion Cardinality
-- Finds Enduring Standards that correctly group multiple edition/versions.
SELECT s.standard_number, COUNT(v.id) as version_count
FROM standards s
JOIN standard_versions v ON s.id = v.standard_id
GROUP BY s.standard_number
HAVING COUNT(v.id) > 1;

-- 5. Check for Orphaned Versions (Must be 0)
SELECT COUNT(*) as orphaned_versions
FROM standard_versions v
LEFT JOIN standards s ON v.standard_id = s.id
WHERE s.id IS NULL;

-- 6. Check Unresolved Relationships
-- Count of relationships where the target standard is unmapped
SELECT COUNT(*) as unresolved_relations
FROM standard_relationships
WHERE target_standard_id IS NULL;

-- 7. Verify Metadata Preservation (JSONB parsing test)
SELECT COUNT(*) as versions_with_metadata
FROM standard_versions
WHERE extra_metadata IS NOT NULL AND extra_metadata != '{}'::jsonb;
