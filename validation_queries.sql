-- ====================================================================
-- Spec2IS Database Validation & Verification Queries
-- ====================================================================

-- 1. Entity and Table Counts
SELECT 'standards' AS table_name, COUNT(*) AS total_count FROM standards
UNION ALL
SELECT 'standard_versions', COUNT(*) FROM standard_versions
UNION ALL
SELECT 'standard_parts', COUNT(*) FROM standard_parts
UNION ALL
SELECT 'standard_relationships', COUNT(*) FROM standard_relationships
UNION ALL
SELECT 'standard_domains', COUNT(*) FROM standard_domains
UNION ALL
SELECT 'standard_keywords', COUNT(*) FROM standard_keywords
UNION ALL
SELECT 'standard_keyword_map', COUNT(*) FROM standard_keyword_map
UNION ALL
SELECT 'standard_sources', COUNT(*) FROM standard_sources
UNION ALL
SELECT 'standard_parameters', COUNT(*) FROM standard_parameters
UNION ALL
SELECT 'standard_embeddings', COUNT(*) FROM standard_embeddings;

-- 2. Standards with missing titles (Integrity check: must be 0)
SELECT id, standard_number, title FROM standards WHERE title IS NULL OR TRIM(title) = '';

-- 3. Versions without parent standards (Foreign key check: must be 0)
SELECT v.id, v.standard_id, v.year 
FROM standard_versions v 
LEFT JOIN standards s ON v.standard_id = s.id 
WHERE s.id IS NULL;

-- 4. Parts without parent versions (Foreign key check: must be 0)
SELECT p.id, p.standard_version_id, p.part_number 
FROM standard_parts p 
LEFT JOIN standard_versions v ON p.standard_version_id = v.id 
WHERE v.id IS NULL;

-- 5. Duplicate standard and version combinations (Uniqueness check: must be 0)
SELECT standard_id, year, COUNT(*) 
FROM standard_versions 
GROUP BY standard_id, year 
HAVING COUNT(*) > 1;

-- 6. Relationships pointing to nonexistent target standards inside our database
SELECT r.id, r.source_standard_id, r.relationship_type, r.target_standard_number_raw, r.notes
FROM standard_relationships r
WHERE r.target_standard_id IS NULL;

-- 7. Conflicting metadata records preserved in standard_versions
SELECT s.standard_number, v.year, v.notes
FROM standard_versions v
JOIN standards s ON v.standard_id = s.id
WHERE v.notes ILIKE '%conflict%';

-- 8. Standards with parts detailed view
SELECT s.standard_number, v.year, p.part_number, p.part_title
FROM standard_parts p
JOIN standard_versions v ON p.standard_version_id = v.id
JOIN standards s ON v.standard_id = s.id
ORDER BY s.standard_number, p.part_number;

-- 9. Standards with explicit relationships
SELECT 
    ss.standard_number AS source_standard,
    sv.year AS source_year,
    r.relationship_type,
    COALESCE(ts.standard_number, r.target_standard_number_raw) AS target_standard,
    tv.year AS target_year,
    r.notes
FROM standard_relationships r
JOIN standards ss ON r.source_standard_id = ss.id
JOIN standard_versions sv ON r.source_version_id = sv.id
LEFT JOIN standards ts ON r.target_standard_id = ts.id
LEFT JOIN standard_versions tv ON r.target_version_id = tv.id
ORDER BY ss.standard_number;

-- 10. Sample verification of multi-version standard (e.g. IS 1642 or IS 2190)
SELECT s.standard_number, s.title, v.year, v.edition, v.status, v.verification_status
FROM standards s
JOIN standard_versions v ON v.standard_id = s.id
WHERE s.standard_number IN ('IS 2190', 'IS 1642', 'IS 15105', 'IS 15908', 'IS 1644')
ORDER BY s.standard_number, v.year;
