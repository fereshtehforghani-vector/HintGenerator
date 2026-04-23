"""
Cloud Run service — query_rag

Called at tutoring time by the front-end. Accepts either:
  * application/json — C++ text path (RAG + analyse_code)
  * multipart/form-data — file upload path:
      - image (.png/.jpg/.jpeg/.webp): uploaded to zebra-robotics-images,
        signed URL returned, analyse_image() runs vision LLM + RAG.
      - .cpp: source text extracted, analyse_code() as above.

Every turn is persisted to the shared ``conversation_history`` table.

Expected fields (either body type):
    query / question : free-text question            (default "")
    code             : student C++ code              (default "" — required if no file)
    provider         : "OpenAI" | "Gemini"           (default "OpenAI")
    course_id        : LMS course slug               (optional)
    conversation_id  : client-supplied session id    (optional)

Response body (JSON):
    {
        "response":        "<Socratic hint markdown>",
        "provider":        "OpenAI",
        "lms_references":  [...],
        "conversation_id": "<echoed back>",
        "stored_file_url": "<signed GCS URL or null>"
    }
"""

import json
import os
import sys
import traceback

from flask import Flask, request

sys.path.insert(0, ".")

from shared.config import COLLECTION_NAME, get_db_engine, get_secret
from shared.conversation_store import save_conversation_turn
from shared.file_handler import process_file
from shared.rag_utils import get_retriever, get_vectorstore
from shared.tutor import AgenticTutor

app = Flask(__name__)

# Module-level cache — vectorstore and engine reused across warm instances.
_engine      = None
_vectorstore = None


def _warm():
    global _engine, _vectorstore
    if _vectorstore is not None:
        return _engine, _vectorstore

    os.environ["GOOGLE_API_KEY"] = get_secret("GOOGLE_API_KEY")
    os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY")
    db_password = get_secret("conversation_history_DB-PASSWORD")

    _engine      = get_db_engine(db_password)
    _vectorstore = get_vectorstore(_engine, COLLECTION_NAME)
    return _engine, _vectorstore


def _parse_body():
    """Return (code, question, provider, course_id, conversation_id,
    file_type, file_data, stored_file_url) from either JSON or multipart."""
    file_type, file_data, stored_file_url = process_file(request)

    if file_type is not None:
        form = request.form
        code      = str(form.get("code", "")).strip()
        question  = str(form.get("question", form.get("query", ""))).strip()
        provider  = str(form.get("provider", "OpenAI"))
        course_id = form.get("course_id") or None
        conv_id   = form.get("conversation_id") or None
    else:
        body = request.get_json(silent=True) or {}
        code      = str(body.get("code", "")).strip()
        question  = str(body.get("question", body.get("query", ""))).strip()
        provider  = str(body.get("provider", "OpenAI"))
        course_id = body.get("course_id") or None
        conv_id   = body.get("conversation_id") or None

    return code, question, provider, course_id, conv_id, file_type, file_data, stored_file_url


@app.route("/", methods=["OPTIONS", "POST"])
def query_rag():
    cors_headers = {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if request.method == "OPTIONS":
        return ("", 204, {**cors_headers, "Access-Control-Max-Age": "3600"})

    try:
        (code, question, provider, course_id, conv_id,
         file_type, file_data, stored_file_url) = _parse_body()

        # For .cpp uploads, the file payload *is* the code.
        if file_type == "cpp":
            code = file_data

        if file_type != "image" and not code:
            return (
                json.dumps({"error": "Provide either 'code' text or an uploaded file."}),
                400,
                {**cors_headers, "Content-Type": "application/json"},
            )

        engine, vs = _warm()
        retriever  = get_retriever(vs, top_k=10, course_id=course_id)
        tutor      = AgenticTutor(provider=provider, retriever=retriever, enable_security=True)

        if file_type == "image":
            result     = tutor.analyse_image(file_data, question)
            user_query = question or "[image submission]"
        else:
            result     = tutor.analyse_code(code, question)
            user_query = f"{question}\n\n{code}".strip() if question else code

        try:
            save_conversation_turn(
                engine,
                conversation_id=conv_id,
                user_query=user_query,
                model_response=result["response"],
                image_url=stored_file_url,
            )
        except Exception as log_err:
            # Logging failure must not break the tutoring response.
            print(f"[warn] conversation_history insert failed: {log_err}")

        return (
            json.dumps({
                "response":        result["response"],
                "lms_references":  result["lms_references"],
                "provider":        provider,
                "conversation_id": conv_id,
                "stored_file_url": stored_file_url,
            }),
            200,
            {**cors_headers, "Content-Type": "application/json"},
        )

    except Exception as exc:
        traceback.print_exc()
        return (
            json.dumps({"error": str(exc)}),
            500,
            {**cors_headers, "Content-Type": "application/json"},
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
