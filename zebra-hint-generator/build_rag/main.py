"""
Cloud Function A — build_rag_database

Triggered via HTTP (manually or on a schedule when documents change).
Downloads all knowledge-base documents from Cloud Storage, chunks them,
embeds with Gemini Embedding 2, and stores vectors in Cloud SQL (pgvector).

Deploy command (see deploy.sh):
    gcloud functions deploy build-rag-database ...
"""

import json
import sys
import traceback

import functions_framework

# Add parent dir so `shared` is importable when deployed alongside this file
sys.path.insert(0, ".")

from shared.config import (
    BUCKET_NAME,
    COLLECTION_NAME,
    get_db_engine,
    get_secret,
)
from shared.data_loaders import download_gcs_documents, load_all_documents
from shared.rag_utils import rebuild_vectorstore


@functions_framework.http
def build_rag_database(request):
    """
    HTTP handler — rebuilds the PGVector collection from scratch.

    Optional JSON body:
        { "dry_run": true }   → download & chunk docs, skip embedding/indexing
    """
    body    = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run", False))

    try:
        # ── 1. Load secrets ────────────────────────────────────────────────
        print("Loading secrets...")
        import os
        os.environ["GOOGLE_API_KEY"] = get_secret("GOOGLE_API_KEY")
        os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY")
        db_password                  = get_secret("DB_PASSWORD")

        # ── 2. Download documents from GCS ─────────────────────────────────
        print(f"Downloading documents from gs://{BUCKET_NAME} ...")
        gcs_paths = download_gcs_documents(BUCKET_NAME)

        # ── 3. Load + chunk ────────────────────────────────────────────────
        print("Loading and chunking documents...")
        chunked_docs = load_all_documents(
            lms_dir       = gcs_paths["lms_dir"],
            libraries_pdf = gcs_paths["libraries_pdf"],
            zebrabot_dir  = gcs_paths.get("zebrabot_dir"),
        )
        print(f"  {len(chunked_docs)} chunks ready.")

        if dry_run:
            return (
                json.dumps({"status": "dry_run", "chunks": len(chunked_docs)}),
                200,
                {"Content-Type": "application/json"},
            )

        # ── 4. Rebuild vectorstore ─────────────────────────────────────────
        print("Connecting to Cloud SQL...")
        engine = get_db_engine(db_password)

        print("Rebuilding PGVector collection...")
        rebuild_vectorstore(chunked_docs, engine, COLLECTION_NAME)

        result = {"status": "success", "chunks_indexed": len(chunked_docs)}
        print(f"Done: {result}")
        return (
            json.dumps(result),
            200,
            {"Content-Type": "application/json"},
        )

    except Exception as exc:
        traceback.print_exc()
        return (
            json.dumps({"status": "error", "message": str(exc)}),
            500,
            {"Content-Type": "application/json"},
        )
