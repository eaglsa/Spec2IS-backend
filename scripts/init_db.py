"""
scripts/init_db.py
------------------
One-shot database initialisation for fresh deployments (e.g. Render).

Steps:
  1. Apply postgresql_schema.sql   — creates all tables + pgvector extension
  2. Apply seed_data.sql — inserts all IS standards metadata
  3. Generate embeddings — populates standard_embeddings via sentence-transformers

Usage (from project root):
    python scripts/init_db.py
    python scripts/init_db.py --skip-schema    # if tables already exist
    python scripts/init_db.py --skip-seed      # if seed data already applied
    python scripts/init_db.py --skip-embed     # skip embedding generation
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def apply_sql_file(db, path: str, label: str) -> None:
    from sqlalchemy import text
    print(f"\n[{label}] Reading {path} ...", flush=True)
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    # Split on statement boundaries and execute each non-empty statement
    # (asyncpg does not support multi-statement strings)
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    print(f"[{label}] Executing {len(statements)} statements...", flush=True)
    for i, stmt in enumerate(statements, 1):
        try:
            await db.execute(text(stmt))
        except Exception as exc:
            # Log but continue — ON CONFLICT errors are fine during re-runs
            print(f"  [warn] stmt {i}: {exc}", flush=True)
    await db.commit()
    print(f"[{label}] Done.", flush=True)


async def run(skip_schema: bool, skip_seed: bool, skip_embed: bool) -> None:
    from db.session import AsyncSessionLocal, engine

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base_dir, "db", "sql", "postgresql_schema.sql")
    seed_path   = os.path.join(base_dir, "db", "sql", "seed_data.sql")

    async with AsyncSessionLocal() as db:
        if not skip_schema:
            await apply_sql_file(db, schema_path, "SCHEMA")
        else:
            print("\n[SCHEMA] Skipped.", flush=True)

        if not skip_seed:
            await apply_sql_file(db, seed_path, "SEED")
        else:
            print("[SEED] Skipped.", flush=True)

    await engine.dispose()

    if not skip_embed:
        print("\n[EMBEDDINGS] Generating embeddings...", flush=True)
        # Import and run the embedding script directly
        from scripts.generate_embeddings import run as gen_embeddings
        await gen_embeddings(force=False)
    else:
        print("[EMBEDDINGS] Skipped.", flush=True)

    print("\n✅ Database initialisation complete!", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialise Spec2IS database")
    parser.add_argument("--skip-schema", action="store_true", help="Skip postgresql_schema.sql")
    parser.add_argument("--skip-seed",   action="store_true", help="Skip seed_data.sql")
    parser.add_argument("--skip-embed",  action="store_true", help="Skip embedding generation")
    args = parser.parse_args()

    start = time.time()
    asyncio.run(run(args.skip_schema, args.skip_seed, args.skip_embed))
    print(f"Total time: {time.time() - start:.1f}s", flush=True)
