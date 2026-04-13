"""
RAG utilities: Gemini Embedding 2 wrapper, vectorstore factory, context builder.

Embedding model : gemini-embedding-2-preview  (3072-d)
Vector store    : PGVector on Cloud SQL (langchain-postgres)
"""

import os
import time
from pathlib import Path
from typing import List

import numpy as np
from langchain_core.documents import Document as LCDoc
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector

SEPARATOR = "─" * 50


# ── Gemini Embedding 2 ─────────────────────────────────────────────────────────
class GeminiEmbedding2(Embeddings):
    """
    LangChain-compatible wrapper for gemini-embedding-2-preview (3072-d).
    Batches document embedding to stay within API rate limits.
    """

    MODEL = "gemini-embedding-2-preview"

    def __init__(self, api_key: str = None, batch_size: int = 20):
        from google import genai as google_genai
        api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")
        self._client = google_genai.Client(api_key=api_key)
        self._batch  = batch_size

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        result = self._client.models.embed_content(
            model=self.MODEL, contents=texts
        )
        return [e.values for e in result.embeddings]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        out = []
        for i in range(0, len(texts), self._batch):
            out.extend(self._embed_batch(texts[i : i + self._batch]))
            if i + self._batch < len(texts):
                time.sleep(0.5)
        return out

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]


# ── Vectorstore helpers ────────────────────────────────────────────────────────
def get_vectorstore(engine, collection_name: str) -> PGVector:
    """Connect to an existing PGVector collection (read path)."""
    return PGVector(
        connection=engine,
        embeddings=GeminiEmbedding2(),
        collection_name=collection_name,
        use_jsonb=True,
    )


def get_retriever(vectorstore: PGVector, top_k: int = 10, course_id: str = None):
    """
    Return a retriever for the given vectorstore.

    If ``course_id`` is provided (e.g. ``"sdv"`` or ``"reactive_robtics"``),
    retrieval is scoped to LMS chunks tagged with that course only — all
    non-LMS chunks (library docs, mistake patterns, firmware) are still
    searched regardless.

    The filter uses PGVector's metadata pre-filter:
        WHERE (cmetadata->>'course_id' = <course_id>)
           OR (cmetadata->>'type' != 'curriculum')
    expressed via LangChain's $or / $ne filter syntax.
    """
    if course_id:
        search_filter = {
            "$or": [
                {"course_id": {"$eq": course_id}},
                {"type":      {"$ne": "curriculum"}},
            ]
        }
        return vectorstore.as_retriever(
            search_kwargs={"k": top_k, "filter": search_filter}
        )
    return vectorstore.as_retriever(search_kwargs={"k": top_k})


def rebuild_vectorstore(docs: list[LCDoc], engine, collection_name: str) -> PGVector:
    """
    Drop and recreate the PGVector collection, then index all documents.
    Called by the build_rag Cloud Function.
    """
    embeddings = GeminiEmbedding2()
    vs = PGVector(
        connection=engine,
        embeddings=embeddings,
        collection_name=collection_name,
        use_jsonb=True,
    )
    print(f"Dropping collection '{collection_name}'...")
    vs.delete_collection()
    vs.create_collection()

    BATCH = 20
    for i in range(0, len(docs), BATCH):
        batch = docs[i : i + BATCH]
        vs.add_documents(batch)
        done = min(i + BATCH, len(docs))
        print(f"  Indexed {done}/{len(docs)} chunks", end="\r")
        time.sleep(0.3)

    print(f"\nCollection '{collection_name}' ready — {len(docs)} chunks.")
    return vs


# ── Context builder ────────────────────────────────────────────────────────────
def build_rag_context(
    query: str = None,
    retriever=None,
    top_k: int = 10,
) -> tuple[str, list[LCDoc]]:
    """
    Retrieve the top-k documents for a text query and format them as a
    numbered context block the LLM can cite as [1], [2], …

    Parameters
    ----------
    query     : text query (student code + question concatenated)
    retriever : LangChain retriever backed by PGVector
    top_k     : number of results (default 10)
    """
    if query is None or retriever is None:
        raise ValueError("query and retriever are required")

    docs = retriever.invoke(query)

    # --- Build the ordered doc list ----------------------------------------
    # 1. Curriculum chunks come first, deduplicated by source file so each
    #    lesson gets exactly one sequential number ([1], [2], ...).
    #    Multiple chunks from the same lesson would create gaps after
    #    deduplication in lms_references, so we keep only the first
    #    (highest-relevance) chunk per lesson.
    # 2. Non-curriculum docs follow, keeping all chunks.
    seen_sources: set[str] = set()
    curriculum_docs = []
    for d in docs:
        if d.metadata.get("type") == "curriculum":
            src = d.metadata.get("source", "")
            if src not in seen_sources:
                seen_sources.add(src)
                curriculum_docs.append(d)

    other_docs = [d for d in docs if d.metadata.get("type") != "curriculum"]
    docs = curriculum_docs + other_docs
    # -----------------------------------------------------------------------

    context_parts = []
    curriculum_idx = 0
    lib_idx        = 0
    for doc in docs:
        doc_type = doc.metadata.get("type", "unknown")
        source   = Path(doc.metadata.get("source", "")).name
        snippet  = doc.page_content[:1200].strip()
        label = {
            "curriculum"       : "📘 Curriculum",
            "library_reference": "📗 Library Docs",
            "mistake_pattern"  : "⚠️  Common Mistake",
            "cpp_example"      : "💻 Code Example",
            "zebrabot_library" : "📗 ZebraBot Library Header",
            "zebrabot_example" : "💻 ZebraBot Example",
        }.get(doc_type, "📄 Reference")

        # Curriculum passages get [1], [2], … — these numbers appear in lms_references.
        # All other passages get [L1], [L2], … to avoid citation collisions.
        if doc_type == "curriculum":
            curriculum_idx += 1
            citation = str(curriculum_idx)
        else:
            lib_idx += 1
            citation = f"L{lib_idx}"

        context_parts.append(
            f"[{citation}] {label} ({source})\n{snippet}\n{SEPARATOR}"
        )

    return "\n\n".join(context_parts), docs


def extract_lms_references(docs: list[LCDoc]) -> list[dict]:
    """
    From a list of retrieved documents, return one entry per unique LMS lesson
    (deduplicated by source file) in the same order they appear in the context.

    The ``ref`` field matches the [N] citation number the LLM used in its
    response (1-indexed position in the docs list), so the front-end can
    link "According to [6]" directly to lms_references entry with ref=6.

        {
            "ref":       6,
            "title":     "Class 6: Coding Sensor",
            "module":    7,
            "course":    "Self Driving Car",
            "course_id": "sdv",
            "content":   "<first 800 chars of the lesson text>"
        }
    """
    refs: list[dict] = []

    for i, doc in enumerate(docs, 1):   # i is the [N] number the LLM sees
        meta = doc.metadata
        if meta.get("type") != "curriculum":
            continue
        # build_rag_context already deduped curriculum by source, so no
        # gaps are possible here — i will be 1, 2, 3, ... for curriculum.
        source = meta.get("source", "")
        try:
            module = int(meta.get("module", 0))
        except (ValueError, TypeError):
            module = 0

        refs.append({
            "ref":       i,
            "title":     meta.get("title", Path(source).stem),
            "module":    module,
            "course":    meta.get("course", ""),
            "course_id": meta.get("course_id", ""),
            "content":   doc.page_content[:800].strip(),
        })

    return refs
