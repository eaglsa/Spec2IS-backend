"""
ETL script to migrate data from the BIS Crawler DB to the Spec2IS Application DB.
Architecture: Crawler DB (Raw) -> ETL -> Spec2IS DB (Normalized).
"""
import os
import json
import asyncio
import logging
import argparse
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import AsyncSessionLocal, engine
from db.models import (
    StandardDomain, 
    Standard, 
    StandardVersion, 
    StandardRelationship
)
from sqlalchemy.future import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

CRAWLER_DB_URL = os.environ.get("CRAWLER_DATABASE_URL", "sqlite:///bis_extractor/output/bis_standards.db")

crawler_engine = create_engine(CRAWLER_DB_URL)
CrawlerSession = sessionmaker(bind=crawler_engine)

def get_core_is_number(raw_is):
    """
    Extracts enduring identity (e.g. 'IS 1234') from 'IS 1234 : 2019'.
    """
    if not raw_is:
        return ""
    m = re.match(r'^(IS\s+[A-Za-z0-9/]+(?:\s*\(Part\s*\d+\))?)', raw_is.strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return raw_is.strip().split(':')[0].strip()

async def check_postgresql_preflight(db_session):
    """Ensure Postgres schema is ready before any import attempts."""
    logger.info("Running PostgreSQL Preflight Validation...")
    
    bind_url = str(db_session.bind.url)
    
    if "sqlite" in bind_url:
        logger.error("ERROR: Production ETL target is SQLite. Expected PostgreSQL. Import aborted before processing records.")
        return False

    try:
        # Check standard_versions columns
        result = await db_session.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='standard_versions'"
        ))
        columns = [row[0] for row in result.fetchall()]
        if 'bis_standard_id' not in columns:
            logger.error("Preflight Failed: 'bis_standard_id' missing from standard_versions. Run migrations.")
            return False
        if 'extra_metadata' not in columns:
            logger.error("Preflight Failed: 'extra_metadata' missing from standard_versions. Run migrations.")
            return False
        
        logger.info("Preflight Passed: Schema requirements verified on PostgreSQL.")
        return True
    except Exception as e:
        logger.error(f"Preflight Failed: Database connection or schema error: {e}")
        return False

async def import_standards(dry_run: bool = False, limit: int = None):
    logger.info(f"Starting ETL pipeline. Dry Run: {dry_run}, Limit: {limit}")
    
    with CrawlerSession() as crawler_session:
        # Check if crawler tables exist
        try:
            departments = crawler_session.execute(text("SELECT department_id, name, url FROM departments")).fetchall()
            limit_clause = f" LIMIT {limit}" if limit else ""
            standards = crawler_session.execute(text(f"""
                SELECT id, department_id, is_number, year, title, status, url, 
                       detail_url, encrypted_id, bis_standard_id 
                FROM standards
                ORDER BY id
                {limit_clause}
            """)).fetchall()
            
            # Extract standard IDs to fetch related details/relationships if limited
            std_ids = [s.id for s in standards]
            if not std_ids:
                logger.info("No standards found in crawler database.")
                return

            placeholders = ','.join(str(s) for s in std_ids)
            details = crawler_session.execute(text(f"SELECT * FROM standard_details WHERE standard_id IN ({placeholders})")).fetchall()
            relationships = crawler_session.execute(text(f"SELECT * FROM standard_relationships WHERE source_standard_id IN ({placeholders})")).fetchall()
            
        except Exception as e:
            logger.error(f"Failed to read from crawler database: {e}")
            return
            
    details_map = {d.standard_id: dict(d._mapping) for d in details}
    
    source_rels = len(relationships)
    logger.info(f"Read from Crawler: {len(departments)} departments, {len(standards)} standards, {source_rels} relationships.")

    stats = {
        "crawler_records": len(standards),
        "new_domains": 0,
        "unique_standards_resolved": 0,
        "new_standards": 0,
        "existing_standards": 0,
        "new_versions": 0,
        "updated_versions": 0,
        "rels_imported": 0,
        "rels_unresolved": 0,
        "records_failed": 0,
        "records_skipped": 0
    }

    print(f"Source database: {CRAWLER_DB_URL.split('://')[0]}")
    print(f"Target database: PostgreSQL (expected)")
    print(f"Source database configured: {'YES' if CRAWLER_DB_URL else 'NO'}")
    print(f"Target database configured: {'YES' if os.environ.get('DATABASE_URL') else 'NO'}")

    async with AsyncSessionLocal() as db:
        if not await check_postgresql_preflight(db):
            print("Target PostgreSQL preflight: FAIL")
            return
        
        print("Target PostgreSQL preflight: PASS")

        domain_map = {}
        for dept in departments:
            name_clean = dept.name.strip().upper()
            result = await db.execute(select(StandardDomain).filter_by(name=name_clean))
            domain = result.scalar_one_or_none()
            if not domain:
                domain = StandardDomain(name=name_clean, description=f"Imported from BIS {dept.department_id}")
                if not dry_run:
                    db.add(domain)
                    await db.flush()
                stats["new_domains"] += 1
            if not dry_run:
                domain_map[dept.department_id] = domain.id

        bis_to_version_id = {}
        is_number_to_std_id = {}

        # First pass: Standards & Versions
        for std in standards:
            try:
                core_is = get_core_is_number(std.is_number)
                if not core_is:
                    logger.warning(f"Skipping standard {std.id}: Invalid is_number '{std.is_number}'")
                    stats["records_skipped"] += 1
                    continue

                # 1. Resolve Enduring Identity (Standard)
                result = await db.execute(select(Standard).filter_by(standard_number=core_is))
                spec_std = result.scalar_one_or_none()
                
                if not spec_std:
                    spec_std = Standard(
                        standard_number=core_is,
                        title=std.title,
                        domain_id=domain_map.get(std.department_id),
                        verification_status="Imported via Crawler"
                    )
                    if not dry_run:
                        db.add(spec_std)
                        await db.flush()
                    stats["new_standards"] += 1
                else:
                    # Update enduring metadata if needed
                    stats["existing_standards"] += 1
                    
                if not dry_run:
                    is_number_to_std_id[core_is] = spec_std.id
                stats["unique_standards_resolved"] += 1

                # 2. Extract rich metadata
                extra = {}
                det = details_map.get(std.id)
                if det:
                    for k, v in det.items():
                        if k not in ['id', 'standard_id', 'scraped_at'] and v:
                            extra[k] = v
                extra["crawler_url"] = std.url
                extra["crawler_detail_url"] = std.detail_url
                if std.encrypted_id:
                    extra["encrypted_id"] = std.encrypted_id

                try:
                    year_val = int(std.year) if std.year and str(std.year).isdigit() else 0
                except:
                    year_val = 0

                # 3. Resolve Edition/Revision (StandardVersion)
                spec_ver = None
                if std.bis_standard_id:
                    result = await db.execute(select(StandardVersion).filter_by(bis_standard_id=std.bis_standard_id))
                    spec_ver = result.scalar_one_or_none()
                
                # Fallback to standard_id + year if bis_id is missing/not found
                if not spec_ver and not dry_run:
                    result = await db.execute(select(StandardVersion).filter_by(standard_id=spec_std.id, year=year_val))
                    spec_ver = result.scalar_one_or_none()

                if not spec_ver:
                    spec_ver = StandardVersion(
                        standard_id=spec_std.id if not dry_run else 0,
                        year=year_val,
                        status=std.status,
                        bis_standard_id=std.bis_standard_id,
                        extra_metadata=extra,
                        verification_status="Imported via Crawler"
                    )
                    if not dry_run:
                        db.add(spec_ver)
                        await db.flush()
                        if std.bis_standard_id:
                            bis_to_version_id[std.bis_standard_id] = spec_ver.id
                    stats["new_versions"] += 1
                else:
                    if not dry_run:
                        spec_ver.status = std.status
                        spec_ver.extra_metadata = extra
                        spec_ver.bis_standard_id = std.bis_standard_id
                        await db.flush()
                        if std.bis_standard_id:
                            bis_to_version_id[std.bis_standard_id] = spec_ver.id
                    stats["updated_versions"] += 1

                if not dry_run:
                    await db.commit() # Commit each standard safely
            except Exception as e:
                logger.error(f"Error processing standard {std.is_number}: {e}")
                await db.rollback()
                stats["records_failed"] += 1

        # Second pass: Relationships
        for rel in relationships:
            try:
                source_std_row = [s for s in standards if s.id == rel.source_standard_id]
                if not source_std_row:
                    continue
                    
                source_std = source_std_row[0]
                
                source_version_id = None
                source_std_id = None
                if not dry_run:
                    if source_std.bis_standard_id in bis_to_version_id:
                        source_version_id = bis_to_version_id[source_std.bis_standard_id]
                    
                    core_is = get_core_is_number(source_std.is_number)
                    source_std_id = is_number_to_std_id.get(core_is)

                if not dry_run and not source_std_id:
                    continue

                target_std_id = None
                target_raw = rel.target_standard_is_number
                target_core = get_core_is_number(target_raw)
                
                if not dry_run:
                    if target_core in is_number_to_std_id:
                        target_std_id = is_number_to_std_id[target_core]
                    else:
                        stats["rels_unresolved"] += 1

                rel_type = rel.relationship_type.upper() if rel.relationship_type else 'RELATED_TO'
                valid_types = ['REVISES', 'REVISED_BY', 'SUPERSEDES', 'SUPERSEDED_BY', 'RELATED_TO', 'WITHDRAWN', 'OTHER']
                if rel_type not in valid_types:
                    rel_type = 'RELATED_TO'

                if not dry_run and source_version_id:
                    result = await db.execute(
                        select(StandardRelationship).filter_by(
                            source_version_id=source_version_id,
                            relationship_type=rel_type,
                            target_standard_number_raw=target_raw
                        )
                    )
                    spec_rel = result.scalar_one_or_none()
                    if not spec_rel:
                        spec_rel = StandardRelationship(
                            source_standard_id=source_std_id,
                            source_version_id=source_version_id,
                            target_standard_id=target_std_id,
                            relationship_type=rel_type,
                            target_standard_number_raw=target_raw,
                            notes=rel.raw_relationship_text
                        )
                        db.add(spec_rel)
                        stats["rels_imported"] += 1
                        await db.commit()
            except Exception as e:
                logger.error(f"Error processing relationship: {e}")
                await db.rollback()

    logger.info("=" * 40)
    logger.info(f"ETL Import Summary (Dry Run: {dry_run})")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import data from Crawler to Spec2IS")
    parser.add_argument("--dry-run", action="store_true", help="Calculate insertions without writing to DB")
    parser.add_argument("--limit", type=int, help="Limit number of crawler records to process")
    args = parser.parse_args()
    
    asyncio.run(import_standards(dry_run=args.dry_run, limit=args.limit))
