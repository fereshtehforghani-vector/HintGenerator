"""
Persist one tutoring turn (student query + model response) to the
``conversation_history`` table on the Cloud SQL instance shared with pgvector.

Schema matches what core_runtime_loop/store_conversation.py originally
created, so legacy rows and new rows coexist:

    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    user_query TEXT NOT NULL,
    model_response TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()

Uses the same SQLAlchemy engine as the RAG path (get_db_engine) — one
connector, one pool, one password secret.
"""

import uuid

from sqlalchemy import text


_schema_ready = False


def _ensure_schema(engine) -> None:
    global _schema_ready
    if _schema_ready:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT,
                user_query      TEXT NOT NULL,
                model_response  TEXT NOT NULL,
                image_url       TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """))
    _schema_ready = True


def save_conversation_turn(
    engine,
    conversation_id: str | None,
    user_query: str,
    model_response: str,
    image_url: str | None = None,
) -> str:
    """Insert one row and return its generated id."""
    _ensure_schema(engine)
    row_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO conversation_history
                    (id, conversation_id, user_query, model_response, image_url)
                VALUES (:id, :cid, :q, :r, :img)
            """),
            {
                "id":  row_id,
                "cid": conversation_id,
                "q":   user_query,
                "r":   model_response,
                "img": image_url,
            },
        )
    return row_id
