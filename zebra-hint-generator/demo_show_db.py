"""
demo_show_db.py — read-only inspection of the pgvector tables that
build_rag wrote to Cloud SQL. Safe for a live demo: only SELECTs.

Reuses shared/config.py so the connection path matches the deployed
build_rag service exactly (Cloud SQL Python Connector + pg8000).

Password resolution order:
  1. $DB_PASSWORD (skips Secret Manager — useful if you don't have
     'Secret Manager Secret Accessor' on the project)
  2. Secret Manager secret 'conversation_history_DB-PASSWORD'

Usage:
    cd zebra-hint-generator
    python3 demo_show_db.py
        ↳ inspects the DB AND uploads chunks_prod.json to the default
          GCS path: gs://zebra-rag-documents/chunks_prod.json
    python3 demo_show_db.py --dump ../AI\\ Pilot/chunks_prod.json
        ↳ override the destination (local path or gs://bucket/object URL).
    python3 demo_show_db.py --no-dump
        ↳ inspect only, skip the chunk dump.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.config import (  # noqa: E402
    COLLECTION_NAME,
    EMBEDDING_DIM,
    GCP_PROJECT_ID,
    get_db_engine,
    get_secret,
)
from sqlalchemy import text  # noqa: E402


# ── output helpers ────────────────────────────────────────────────────────────
def cyan(s):    return f"\033[1;36m{s}\033[0m"
def green(s):   return f"\033[1;32m{s}\033[0m"
def yellow(s):  return f"\033[1;33m{s}\033[0m"
def red(s):     return f"\033[1;31m{s}\033[0m"
def dim(s):     return f"\033[2m{s}\033[0m"

def section(title):
    print()
    print(cyan(f"── {title} ──"))


def resolve_password() -> str:
    pw = os.environ.get("DB_PASSWORD")
    if pw:
        print(dim("  (using DB_PASSWORD from environment)"))
        return pw
    try:
        return get_secret("conversation_history_DB-PASSWORD")
    except Exception as e:
        sys.exit(red(
            "Could not read DB_PASSWORD.\n"
            f"  Secret Manager error: {e}\n"
            "  Either grant 'Secret Manager Secret Accessor' to your account,\n"
            "  or  export DB_PASSWORD=<password>  before running this script."
        ))


def _print_row_anatomy(cmetadata, document, emb_head):
    """Print one DB row in a layout that's readable on stage."""
    meta = cmetadata if isinstance(cmetadata, dict) else json.loads(cmetadata or "{}")

    rows = [
        ("source",     meta.get("source")),
        ("type",       meta.get("type")),
        ("modality",   meta.get("modality") or ("image" if meta.get("is_image") else "text")),
        ("course_id",  meta.get("course_id")),
        ("module",     meta.get("module")),
        ("title",      meta.get("title")),
    ]
    if meta.get("is_image"):
        rows += [
            ("image_url", meta.get("image_url")),
            ("alt text",  meta.get("alt")),
        ]
    for k, v in rows:
        if v not in (None, ""):
            print(f"  {k:14}: {v}")

    snippet = (document or "").replace("\n", " ")
    if len(snippet) > 240:
        snippet = snippet[:240] + "..."
    print(f"  {'page_content':14}: {snippet!r}  ({len(document or '')} chars)")

    emb_str = "[" + ", ".join(f"{v:+.4f}" for v in emb_head) + f", ... ]   (× {EMBEDDING_DIM} dims)"
    print(f"  {'embedding':14}: {emb_str}")


def dump_chunks(conn, dest: str) -> tuple[int, str]:
    """Dump every chunk in the active collection to either a local path or
    a gs://bucket/object URL. Returns (row_count, resolved_destination)."""
    rows = conn.execute(text("""
        SELECT e.document, e.cmetadata
          FROM langchain_pg_embedding e
          JOIN langchain_pg_collection c ON e.collection_id = c.uuid
         WHERE c.name = :name
         ORDER BY e.cmetadata->>'type', e.cmetadata->>'source';
    """), {"name": COLLECTION_NAME})

    serialized = []
    for document, cmetadata in rows:
        meta = cmetadata if isinstance(cmetadata, dict) else json.loads(cmetadata or "{}")
        serialized.append({"page_content": document, "metadata": meta})

    payload = json.dumps(serialized, indent=2, ensure_ascii=False)

    if dest.startswith("gs://"):
        from google.cloud import storage
        rest = dest[len("gs://"):]
        if "/" not in rest:
            raise ValueError(f"GCS URL is missing an object path: {dest}")
        bucket_name, _, object_name = rest.partition("/")
        client = storage.Client(project=GCP_PROJECT_ID)
        blob   = client.bucket(bucket_name).blob(object_name)
        blob.upload_from_string(payload, content_type="application/json")
        resolved = f"gs://{bucket_name}/{object_name}"
    else:
        out = Path(dest).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload)
        resolved = str(out)

    return len(serialized), resolved


DEFAULT_DUMP_DEST = "gs://zebra-rag-documents/chunks_prod.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dump", metavar="PATH", default=DEFAULT_DUMP_DEST,
                        help=f"Write every chunk to PATH as JSON. Local path "
                             f"or gs://bucket/object. Default: {DEFAULT_DUMP_DEST}")
    parser.add_argument("--no-dump", action="store_true",
                        help="Skip the chunk dump entirely (inspect only).")
    args = parser.parse_args()
    if args.no_dump:
        args.dump = None

    print(cyan("Connecting to Cloud SQL via the Cloud SQL Python Connector..."))
    db_password = resolve_password()
    engine = get_db_engine(db_password)

    with engine.connect() as conn:
        # ── 1. Collections registered in pgvector ────────────────────────────
        section("Collections in pgvector  (langchain_pg_collection)")
        rows = list(conn.execute(text(
            "SELECT name, uuid, cmetadata FROM langchain_pg_collection ORDER BY name;"
        )))
        if not rows:
            print(yellow("  (none — build_rag has never run successfully)"))
            return
        for name, uuid, cmetadata in rows:
            marker = green("  ◆") if name == COLLECTION_NAME else "  ◇"
            print(f"{marker} {name:24}  uuid={uuid}")
        print(dim(f"  ◆ = the active collection ({COLLECTION_NAME})"))

        # ── 2. Schema of the embedding table ──────────────────────────────────
        section("Schema of langchain_pg_embedding")
        for col, dtype, udt in conn.execute(text("""
            SELECT column_name, data_type, udt_name
              FROM information_schema.columns
             WHERE table_name = 'langchain_pg_embedding'
             ORDER BY ordinal_position;
        """)):
            type_str = f"{dtype} ({udt})" if dtype == "USER-DEFINED" else dtype
            print(f"  {col:20}  {type_str}")

        # ── 3. Confirm the vector dimension ──────────────────────────────────
        section("Embedding dimension (sampled from one row)")
        n = conn.execute(text("""
            SELECT vector_dims(e.embedding)
              FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name
             LIMIT 1;
        """), {"name": COLLECTION_NAME}).scalar()
        match = green("matches") if n == EMBEDDING_DIM else red("MISMATCH vs")
        print(f"  {n}   {dim(match)} {dim(f'EMBEDDING_DIM={EMBEDDING_DIM} in shared/config.py')}")

        # ── 4. Total chunks ──────────────────────────────────────────────────
        section("Total chunks indexed")
        total = conn.execute(text("""
            SELECT count(*) FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name;
        """), {"name": COLLECTION_NAME}).scalar()
        print(f"  {total}")

        # ── 5. Chunks by type ────────────────────────────────────────────────
        section("Chunks by type")
        for chunk_type, count in conn.execute(text("""
            SELECT e.cmetadata->>'type' AS t, count(*) AS n
              FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name
             GROUP BY 1 ORDER BY 2 DESC;
        """), {"name": COLLECTION_NAME}):
            print(f"  {chunk_type or '(null)':24}  {count:>6}")

        # ── 6. Curriculum chunks by course ───────────────────────────────────
        section("Curriculum chunks by course_id")
        for course, count in conn.execute(text("""
            SELECT e.cmetadata->>'course_id' AS course, count(*) AS n
              FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name
               AND e.cmetadata->>'type' = 'curriculum'
             GROUP BY 1 ORDER BY 2 DESC;
        """), {"name": COLLECTION_NAME}):
            print(f"  {course or '(null)':24}  {count:>6}")

        # ── 7. A few sample rows so the audience sees real data ─────────────
        section("Sample chunks (largest 2 per type)")
        for chunk_type, course, source, chars in conn.execute(text("""
            WITH ranked AS (
              SELECT e.cmetadata->>'type'      AS t,
                     e.cmetadata->>'course_id' AS course,
                     e.cmetadata->>'source'    AS source,
                     length(e.document)        AS chars,
                     row_number() OVER (
                       PARTITION BY e.cmetadata->>'type'
                       ORDER BY length(e.document) DESC
                     ) AS rn
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
               WHERE c.name = :name
            )
            SELECT t, course, source, chars
              FROM ranked WHERE rn <= 2
              ORDER BY t, chars DESC;
        """), {"name": COLLECTION_NAME}):
            short = (source or "").rsplit("/", 1)[-1] or "(no source)"
            print(f"  type={chunk_type or '?':20}  course={course or '-':16}  "
                  f"chars={chars:>5}  source={short}")

        # ── 8. Anatomy of one TEXT row and one IMAGE row ─────────────────────
        # Show the full record (metadata + page_content + first 6 floats of
        # the 3072-d embedding) so the audience sees what a vector row really
        # looks like for each modality.
        section("Anatomy of one row · TEXT chunk")
        text_row = conn.execute(text("""
            SELECT e.cmetadata, e.document,
                   (e.embedding::real[])[1:6] AS emb_head
              FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name
               AND COALESCE((e.cmetadata->>'is_image')::boolean, false) = false
               AND length(e.document) > 200
             ORDER BY e.id
             LIMIT 1;
        """), {"name": COLLECTION_NAME}).first()
        if text_row is None:
            print(yellow("  (no text chunks found)"))
        else:
            _print_row_anatomy(*text_row)

        section("Anatomy of one row · IMAGE chunk")
        image_row = conn.execute(text("""
            SELECT e.cmetadata, e.document,
                   (e.embedding::real[])[1:6] AS emb_head
              FROM langchain_pg_embedding e
              JOIN langchain_pg_collection c ON e.collection_id = c.uuid
             WHERE c.name = :name
               AND COALESCE((e.cmetadata->>'is_image')::boolean, false) = true
             ORDER BY e.id
             LIMIT 1;
        """), {"name": COLLECTION_NAME}).first()
        if image_row is None:
            print(yellow("  (no image chunks found — was build_rag run on a"
                         " bucket with parsed-LMS image references?)"))
        else:
            _print_row_anatomy(*image_row)

        # ── 9. Optional: dump every chunk to JSON ────────────────────────────
        if args.dump:
            section(f"Dumping all chunks → {args.dump}")
            n, resolved = dump_chunks(conn, args.dump)
            print(f"  {n} chunks written to {resolved}.")

    print()
    print(green("✓ Read-only inspection complete. No writes were performed."))


if __name__ == "__main__":
    main()
