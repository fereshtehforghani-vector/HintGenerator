"""
GCP project configuration and infrastructure helpers.

Provides:
  - Project / resource constants
  - Secret Manager access
  - Cloud SQL engine factory (via Cloud SQL Python Connector + pg8000)
"""

import os

# ── GCP constants ──────────────────────────────────────────────────────────────
GCP_PROJECT_ID          = "zebra-ai-assist-poc"
# Single Cloud SQL instance holds both pgvector tables and the
# `conversation_history` table used by the legacy block-code tutor.
INSTANCE_CONNECTION_NAME = "zebra-ai-assist-poc:us-central1:zebra-robotics-convo-history"
DB_NAME                 = "zebra_db"
DB_USER                 = "zebra_db_user"
BUCKET_NAME             = "zebra-rag-documents"       # RAG source docs
UPLOAD_BUCKET_NAME      = "zebra-robotics-images"     # student file uploads
COLLECTION_NAME         = "zbot_rag_gcp"
EMBEDDING_DIM           = 3072   # Gemini Embedding 2 output dimension


# ── Secret Manager ─────────────────────────────────────────────────────────────
def get_secret(secret_id: str) -> str:
    """Fetch the latest version of a secret from GCP Secret Manager."""
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    name   = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
    resp   = client.access_secret_version(request={"name": name})
    return resp.payload.data.decode("UTF-8")


# ── Cloud SQL engine ───────────────────────────────────────────────────────────
def get_db_engine(db_password: str):
    """
    Build a SQLAlchemy engine connected to Cloud SQL via the Cloud SQL
    Python Connector (pg8000 driver — pure Python, no system libs needed).

    Inside a Cloud Function the connector uses the Unix socket automatically.
    For local testing, set GOOGLE_APPLICATION_CREDENTIALS and run the
    Cloud SQL Auth Proxy on localhost:5432.
    """
    from google.cloud.sql.connector import Connector
    from sqlalchemy import create_engine

    connector = Connector()

    def _getconn():
        return connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=db_password,
            db=DB_NAME,
        )

    return create_engine(
        "postgresql+pg8000://",
        creator=_getconn,
        pool_size=5,
        max_overflow=2,
        pool_pre_ping=True,
    )
