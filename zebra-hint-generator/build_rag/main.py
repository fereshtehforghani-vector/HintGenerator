"""
Cloud Run service — build_rag_database

Triggered via HTTP (manually or on a schedule when documents change).
Downloads all knowledge-base documents from Cloud Storage, chunks them,
embeds with Gemini Embedding 2, and stores vectors in Cloud SQL (pgvector).

Deploy command (see deploy.sh):
    gcloud run deploy build-rag-database --source build_rag/ ...
"""

import json
import os
import sys
import traceback

from flask import Flask, request

sys.path.insert(0, ".")

from shared.config import (
    BUCKET_NAME,
    COLLECTION_NAME,
    get_db_engine,
    get_secret,
)
from shared.data_loaders import download_gcs_documents, load_all_documents
from shared.rag_utils import rebuild_vectorstore

app = Flask(__name__)


@app.route("/", methods=["POST"])
def build_rag_database():
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
        os.environ["GOOGLE_API_KEY"] = get_secret("GOOGLE_API_KEY")
        os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY")
        db_password                  = get_secret("DB_PASSWORD")

        # ── 2. Download documents from GCS ─────────────────────────────────
        print(f"Downloading documents from gs://{BUCKET_NAME} ...")
        gcs_paths = download_gcs_documents(BUCKET_NAME)

        # ── 3. Load + chunk ────────────────────────────────────────────────
        print("Loading and chunking documents...")
        # LMS files under gcs_paths["lms_dir"] (= /tmp/LMS) mirror blobs under
        # the bucket's "LMS/" prefix — turn the local path back into a GCS URL
        # so the frontend can render clickable lesson links.
        lms_url_prefix = f"https://storage.cloud.google.com/{BUCKET_NAME}/LMS"
        chunked_docs = load_all_documents(
            lms_dir               = gcs_paths["lms_dir"],
            libraries_pdf         = gcs_paths["libraries_pdf"],
            zebrabot_dir          = gcs_paths.get("zebrabot_dir"),
            lms_source_url_prefix = lms_url_prefix,
        )
        print(f"  {len(chunked_docs)} chunks ready.")

        if dry_run:
            return app.response_class(
                response=json.dumps({"status": "dry_run", "chunks": len(chunked_docs)}),
                status=200,
                mimetype="application/json",
            )

        # ── 4. Rebuild vectorstore ─────────────────────────────────────────
        print("Connecting to Cloud SQL...")
        engine = get_db_engine(db_password)

        print("Rebuilding PGVector collection...")
        rebuild_vectorstore(chunked_docs, engine, COLLECTION_NAME)

        result = {"status": "success", "chunks_indexed": len(chunked_docs)}
        print(f"Done: {result}")
        return app.response_class(
            response=json.dumps(result),
            status=200,
            mimetype="application/json",
        )

    except Exception as exc:
        traceback.print_exc()
        return app.response_class(
            response=json.dumps({"status": "error", "message": str(exc)}),
            status=500,
            mimetype="application/json",
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
