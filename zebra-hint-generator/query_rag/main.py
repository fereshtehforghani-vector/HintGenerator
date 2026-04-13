"""
Cloud Function B — query_rag

Called at tutoring time by the front-end (or any HTTP client).
Receives student C++ code + optional question, runs RAG retrieval against
the pgvector collection, calls the LLM, and returns the Socratic hint.

Deploy command (see deploy.sh):
    gcloud functions deploy query-rag ...

Expected request body (JSON):
    {
        "code":      "<student C++ code>",
        "question":  "<optional free-text question>",   // default ""
        "provider":  "OpenAI" | "Gemini",               // default "OpenAI"
        "course_id": "<course slug>"                    // optional — e.g. "sdv", "reactive_robtics"
    }

    When course_id is provided, LMS chunks are filtered to that course only.
    Non-LMS content (library docs, mistake patterns, firmware) is always searched.

Response body (JSON):
    {
        "response":  "<Socratic hint markdown>",
        "provider":  "OpenAI"
    }
"""

import json
import os
import sys
import traceback

import functions_framework

sys.path.insert(0, ".")

from shared.config import COLLECTION_NAME, get_db_engine, get_secret
from shared.rag_utils import get_retriever, get_vectorstore
from shared.tutor import AgenticTutor


# Module-level cache — vectorstore is reused across warm invocations.
# Retrievers are cheap to build and carry the course_id filter, so they
# are created per request rather than cached.
_engine      = None
_vectorstore = None


def _get_vectorstore():
    global _engine, _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    os.environ["GOOGLE_API_KEY"] = get_secret("GOOGLE_API_KEY")
    os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY")
    db_password = get_secret("DB_PASSWORD")

    _engine      = get_db_engine(db_password)
    _vectorstore = get_vectorstore(_engine, COLLECTION_NAME)
    return _vectorstore


@functions_framework.http
def query_rag(request):
    """
    HTTP handler — returns a Socratic tutoring hint for the submitted code.
    """
    # ── CORS pre-flight ────────────────────────────────────────────────────
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age":       "3600",
        }
        return ("", 204, headers)

    cors_headers = {"Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"}

    try:
        body      = request.get_json(silent=True) or {}
        code      = str(body.get("code",      "")).strip()
        question  = str(body.get("question",  "")).strip()
        provider  = str(body.get("provider",  "OpenAI"))
        course_id = body.get("course_id") or None   # None → search all courses

        if not code:
            return (
                json.dumps({"error": "Missing 'code' field in request body."}),
                400,
                cors_headers,
            )

        vs        = _get_vectorstore()
        retriever = get_retriever(vs, top_k=10, course_id=course_id)
        tutor     = AgenticTutor(
            provider=provider,
            retriever=retriever,
            enable_security=True,
        )
        response = tutor.analyse_code(code, question)

        return (
            json.dumps({"response": response, "provider": provider}),
            200,
            cors_headers,
        )

    except Exception as exc:
        traceback.print_exc()
        return (
            json.dumps({"error": str(exc)}),
            500,
            cors_headers,
        )
