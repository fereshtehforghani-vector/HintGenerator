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

from flask import Flask, request, Response, stream_with_context
from sqlalchemy import text

sys.path.insert(0, ".")

from shared.config import COLLECTION_NAME, get_db_engine, get_secret
from shared.conversation_store import save_conversation_turn
from shared.file_handler import process_file
from shared.rag_utils import get_retriever, get_vectorstore
from shared.tutor import AgenticTutor

app = Flask(__name__)

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
    student_id, file_type, file_data, stored_file_url) from either JSON or multipart."""
    file_type, file_data, stored_file_url = process_file(request)

    if file_type is not None:
        form       = request.form
        code       = str(form.get("code", "")).strip()
        question   = str(form.get("question", form.get("query", ""))).strip()
        provider   = str(form.get("provider", "OpenAI"))
        student_id = int(form.get("student_id", 0))
        course_id  = form.get("course_id") or None
        conv_id    = form.get("conversation_id") or None
    else:
        body       = request.get_json(silent=True) or {}
        code       = str(request.form.get("code", body.get("code", ""))).strip()
        question   = str(request.form.get("question", request.form.get("query",
                         body.get("question", body.get("query", ""))))).strip()
        provider   = str(request.form.get("provider", body.get("provider", "OpenAI")))
        student_id = int(request.form.get("student_id", body.get("student_id", 0)))
        course_id  = request.form.get("course_id") or body.get("course_id") or None
        conv_id    = request.form.get("conversation_id") or body.get("conversation_id") or None

    return code, question, provider, course_id, conv_id, student_id, file_type, file_data, stored_file_url


@app.route("/", methods=["OPTIONS", "POST"])
def query_rag():
    cors_headers = {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    if request.method == "OPTIONS":
        return ("", 204, {**cors_headers, "Access-Control-Max-Age": "3600"})

    try:
        (code, question, provider, course_id, conv_id,
         student_id, file_type, file_data, stored_file_url) = _parse_body()

        # For .cpp uploads, the file payload is the code
        if file_type == "cpp":
            code = file_data

        engine, vs = _warm()

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT track FROM students WHERE student_id = :sid"),
                {"sid": student_id},
            ).fetchone()
        track = ((row[0] if row else None) or "cpp").lower()

        if track == "cpp" and not code:
            return (
                "Please paste your C++ code or attach a .cpp file.",
                400,
                {**cors_headers, "Content-Type": "text/plain"},
            )
        if track == "scratch" and file_type != "image":
            return (
                "Please attach your image file.",
                400,
                {**cors_headers, "Content-Type": "text/plain"},
            )

        retriever  = get_retriever(vs, top_k=10, course_id=course_id)
        tutor = AgenticTutor(engine=engine, student_id=student_id, conversation_id=conv_id, provider=provider, retriever=retriever, enable_security=True)

        if file_type == "image":
            result     = tutor.analyse_image(file_data, question)  # file_data is bytes
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
            print(f"[warn] conversation_history insert failed: {log_err}")

        # Stream the response back as plain text so test_frontend.py
        # can display it word by word
        response_text = result["response"]

        def generate():
            # Yield response in small chunks for streaming effect
            chunk_size = 20
            for i in range(0, len(response_text), chunk_size):
                yield response_text[i:i + chunk_size]

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
            headers={
                **cors_headers,
                "X-Conversation-ID": conv_id or "",
                "X-LMS-References": json.dumps(result.get("lms_references", [])),
            }
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