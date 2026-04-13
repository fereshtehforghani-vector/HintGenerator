"""
Local test script — runs build + query against the local Postgres DB
without GCP (no Secret Manager, no GCS).

Usage:
    cd zebra-hint-generator
    GOOGLE_API_KEY=<key> OPENAI_API_KEY=<key> \
        python3 test_local.py [build|query|both]   (default: both)
"""

import json
import os
import sys
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT     = Path(__file__).parent.parent
LMS_DIR       = REPO_ROOT / "AI Pilot/Vector_AI/LMS/LMS_PARSED"
LIBRARIES_PDF = REPO_ROOT / "AI Pilot/Vector_AI/libraries.pdf"

LOCAL_DB_URL    = "postgresql+psycopg://fereshteh@localhost:5432/zbot_rag"
COLLECTION_NAME = "zbot_chunks"
CHUNKS_JSON     = REPO_ROOT / "AI Pilot/chunks.json"

sys.path.insert(0, str(Path(__file__).parent))
from shared.data_loaders import load_all_documents
from shared.rag_utils import get_retriever, get_vectorstore, rebuild_vectorstore
from sqlalchemy import create_engine


def get_local_engine():
    return create_engine(LOCAL_DB_URL)


# ── BUILD ──────────────────────────────────────────────────────────────────────
def run_build():
    print("\n=== BUILD: loading and chunking documents ===")
    docs = load_all_documents(
        lms_dir       = LMS_DIR,
        libraries_pdf = LIBRARIES_PDF,
    )
    # Save chunks to JSON for inspection
    serialized = [
        {"page_content": d.page_content, "metadata": d.metadata}
        for d in docs
    ]
    CHUNKS_JSON.write_text(json.dumps(serialized, indent=2, ensure_ascii=False))
    print(f"  Chunks saved to {CHUNKS_JSON}")

    print(f"\n=== BUILD: indexing {len(docs)} chunks into pgvector ===")
    engine = get_local_engine()
    rebuild_vectorstore(docs, engine, COLLECTION_NAME)
    print("=== BUILD complete ===\n")


# ── QUERY ──────────────────────────────────────────────────────────────────────
TEST_CASES = [
    {
        "label":     "No course filter",
        "code":      "#include <Arduino.h>\nvoid loop() { Serial.println(dist); }",
        "question":  "Why is dist always 0?",
        "course_id": None,
    },
    {
        "label":     "SDV course only",
        "code":      "#include <Arduino.h>\nvoid loop() { Serial.println(dist); }",
        "question":  "Why is dist always 0?",
        "course_id": "sdv",
    },
    {
        "label":     "reactive_robtics course only",
        "code":      "#include <Arduino.h>\nvoid loop() { Serial.println(dist); }",
        "question":  "Why is dist always 0?",
        "course_id": "reactive_robtics",
    },
]


def run_query():
    print("\n=== QUERY: testing retrieval ===")
    engine = get_local_engine()
    vs     = get_vectorstore(engine, COLLECTION_NAME)

    for tc in TEST_CASES:
        retriever = get_retriever(vs, top_k=5, course_id=tc["course_id"])
        query     = tc["code"] + "\n" + tc["question"]
        docs      = retriever.invoke(query)

        print(f"\n--- {tc['label']} (course_id={tc['course_id']!r}) ---")
        print(f"  Retrieved {len(docs)} chunks:")
        for i, d in enumerate(docs, 1):
            cid = d.metadata.get("course_id", "-")
            typ = d.metadata.get("type", "-")
            src = Path(d.metadata.get("source", "")).name
            print(f"  [{i}] type={typ:20s}  course_id={cid:20s}  file={src}")

        # Verify the filter is working
        if tc["course_id"]:
            wrong = [
                d for d in docs
                if d.metadata.get("type") == "curriculum"
                and d.metadata.get("course_id") != tc["course_id"]
            ]
            if wrong:
                print(f"  FAIL: {len(wrong)} chunk(s) from wrong course leaked through!")
            else:
                print(f"  PASS: all curriculum chunks belong to '{tc['course_id']}'")

    print("\n=== QUERY complete ===\n")


# ── main ───────────────────────────────────────────────────────────────────────
mode = sys.argv[1] if len(sys.argv) > 1 else "both"
os.environ["OPENAI_API_KEY"] = "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"
os.environ["GOOGLE_API_KEY"] = "AIzaSyDYY0bGO3_hLioavpepRuHtyazrv8qU0yA"

if mode in ("build", "both"):
    run_build()
if mode in ("query", "both"):
    run_query()
