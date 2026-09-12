"""
scripts/generate_embeddings.py
-------------------------------
Generate sentence-transformer embeddings for all standards and insert them
into the standard_embeddings table.

    python scripts/generate_embeddings.py
    python scripts/generate_embeddings.py --force
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_SIZE = 32


def _build_text(std_number, title, description, notes) -> str:
    parts = [p for p in [std_number, title, description, notes] if p]
    return " | ".join(parts)


async def run(force: bool = False) -> None:
    # Import heavy deps here so prints appear before blocking imports
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}", flush=True)
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("Model loaded.", flush=True)

    from sqlalchemy import delete, select, text
    from db.session import AsyncSessionLocal, engine
    from db.models import Standard, StandardEmbedding, StandardVersion

    print("Connecting to database...", flush=True)
    async with AsyncSessionLocal() as db:
        print("Connected.", flush=True)

        # Check existing
        existing_result = await db.execute(select(StandardEmbedding.standard_id))
        existing_ids = {row[0] for row in existing_result.fetchall()}
        print(f"Existing embeddings: {len(existing_ids)}", flush=True)

        # Load all standards
        standards_result = await db.execute(
            select(Standard.id, Standard.standard_number, Standard.title, Standard.description)
            .order_by(Standard.id)
        )
        standards = standards_result.fetchall()  # list of (id, number, title, desc)
        print(f"Total standards: {len(standards)}", flush=True)

        to_process = (
            standards if force
            else [s for s in standards if s[0] not in existing_ids]
        )
        print(f"To embed: {len(to_process)}", flush=True)

        if not to_process:
            print("Nothing to do. Use --force to re-embed all.")
            await engine.dispose()
            return

        if force and existing_ids:
            ids_to_delete = [s[0] for s in to_process]
            await db.execute(
                delete(StandardEmbedding).where(StandardEmbedding.standard_id.in_(ids_to_delete))
            )
            await db.commit()
            print("Deleted old embeddings.", flush=True)

        # Batch-load all latest versions in ONE query (DISTINCT ON)
        print("Loading latest versions for all standards...", flush=True)
        version_result = await db.execute(text("""
            SELECT DISTINCT ON (standard_id)
                standard_id, id as version_id, notes
            FROM standard_versions
            ORDER BY standard_id, year DESC NULLS LAST
        """))
        version_map = {row[0]: (row[1], row[2]) for row in version_result.fetchall()}
        print(f"Loaded versions for {len(version_map)} standards.", flush=True)

        total = len(to_process)
        inserted = 0

        for batch_start in range(0, total, BATCH_SIZE):
            batch = to_process[batch_start:batch_start + BATCH_SIZE]
            texts = []
            for sid, std_number, title, description in batch:
                vid, notes = version_map.get(sid, (None, None))
                texts.append(_build_text(std_number, title, description, notes))

            batch_num = batch_start // BATCH_SIZE + 1
            print(f"  Encoding batch {batch_num} ({batch_start+1}-{min(batch_start+BATCH_SIZE, total)} of {total})...", flush=True)
            vectors = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)

            for (sid, std_number, title, description), vec, txt in zip(batch, vectors, texts):
                vid, _ = version_map.get(sid, (None, None))
                vec_str = "[" + ",".join(str(x) for x in vec.tolist()) + "]"
                await db.execute(
                    text("""
                        INSERT INTO standard_embeddings
                            (standard_id, standard_version_id, embedding, embedding_model, text_content)
                        VALUES (:sid, :vid, CAST(:vec AS vector), :model, :txt)
                        ON CONFLICT DO NOTHING
                    """),
                    {"sid": sid, "vid": vid, "vec": vec_str,
                     "model": EMBEDDING_MODEL_NAME, "txt": txt},
                )
                inserted += 1

            await db.commit()
            print(f"    -> Committed {inserted}/{total}", flush=True)

    await engine.dispose()
    print(f"\nDone! Inserted {inserted} embeddings into standard_embeddings.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-generate even if embeddings already exist")
    args = parser.parse_args()
    asyncio.run(run(force=args.force))
