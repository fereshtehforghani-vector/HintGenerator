"""
RAG utilities: Gemini Embedding 2 wrapper, vectorstore factory, context builder.

Embedding model : gemini-embedding-2-preview  (3072-d)
Vector store    : PGVector on Cloud SQL (langchain-postgres)
"""

import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

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

    def _call_with_retry(self, **kwargs):
        """Call embed_content with exponential backoff on 429 RESOURCE_EXHAUSTED."""
        from google.genai.errors import ClientError
        delay = 2.0
        for attempt in range(6):
            try:
                return self._client.models.embed_content(**kwargs)
            except ClientError as e:
                if getattr(e, "code", None) != 429 or attempt == 5:
                    raise
                print(f"  [429] backing off {delay:.1f}s (attempt {attempt + 1}/5)")
                time.sleep(delay)
                delay *= 2

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        # gemini-embedding-2-preview treats `contents=[t1, t2, ...]` as parts
        # of one document and returns a single combined embedding. We must
        # call embed_content once per text to get one embedding per text.
        out: List[List[float]] = []
        for text in texts:
            result = self._call_with_retry(model=self.MODEL, contents=text)
            out.append(result.embeddings[0].values)
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        out = []
        for i in range(0, len(texts), self._batch):
            out.extend(self._embed_batch(texts[i : i + self._batch]))
            if i + self._batch < len(texts):
                time.sleep(1.0)
        return out

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]

    def embed_images(self, urls: List[str]) -> List[Optional[List[float]]]:
        """Embed images multimodally by URL.

        Downloads each image and passes its raw bytes to gemini-embedding-2
        as an image Part. Processed one at a time — the SDK's batching for
        ``embed_content`` is text-oriented and mixing image parts into a
        single request is unreliable.

        Returns a list parallel to ``urls``. Entries are ``None`` for URLs
        whose fetch failed (e.g. 403/404 on dead assets); the caller is
        expected to filter these out. Fetch failures are logged but do not
        abort the whole build.
        """
        from google.genai import types

        out: List[Optional[List[float]]] = []
        for url in urls:
            try:
                img_bytes, mime = _download_image(url)
            except Exception as e:
                print(f"  [skip image] {type(e).__name__}: {url}")
                out.append(None)
                continue
            part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
            result = self._call_with_retry(
                model=self.MODEL,
                contents=types.Content(parts=[part]),
            )
            out.append(result.embeddings[0].values)
            time.sleep(0.5)
        return out


_GCS_URL_RE = re.compile(
    r"^https?://(?:storage\.cloud\.google\.com|storage\.googleapis\.com)/"
    r"(?P<bucket>[^/]+)/(?P<object>.+)$"
)


def _download_image(url: str, timeout: int = 30) -> tuple[bytes, str]:
    """Fetch an image URL and return (bytes, mime_type).

    GCS URLs (``storage.cloud.google.com`` / ``storage.googleapis.com``) are
    fetched through the authenticated ``google-cloud-storage`` client so
    private curriculum buckets work. All other URLs use plain HTTP.
    """
    m = _GCS_URL_RE.match(url)
    if m:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(m.group("bucket"))
        blob   = bucket.blob(urllib.parse.unquote(m.group("object")))
        data   = blob.download_as_bytes(timeout=timeout)
        ctype  = blob.content_type or mimetypes.guess_type(url)[0] or "image/png"
        return data, ctype

    req = urllib.request.Request(url, headers={"User-Agent": "zebra-rag/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = resp.headers.get_content_type()
    if not ctype or not ctype.startswith("image/"):
        ctype = mimetypes.guess_type(url)[0] or "image/png"
    return data, ctype


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

    Text docs are embedded through the standard LangChain path. Image docs
    (``metadata["is_image"] == True``) are embedded multimodally with
    ``GeminiEmbedding2.embed_images`` and written via ``add_embeddings``
    so the precomputed image vectors bypass the default text embedder.
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

    text_docs  = [d for d in docs if not d.metadata.get("is_image")]
    image_docs = [d for d in docs if d.metadata.get("is_image")]

    BATCH = 20
    for i in range(0, len(text_docs), BATCH):
        batch = text_docs[i : i + BATCH]
        vs.add_documents(batch)
        done = min(i + BATCH, len(text_docs))
        print(f"  Indexed {done}/{len(text_docs)} text chunks", end="\r")
        time.sleep(0.3)
    if text_docs:
        print()

    indexed_images = 0
    if image_docs:
        print(f"Embedding {len(image_docs)} images...")
        urls       = [d.metadata["image_url"] for d in image_docs]
        image_vecs = embeddings.embed_images(urls)
        # Drop entries whose fetch failed (embed_images returns None for those).
        ok_texts, ok_vecs, ok_metas = [], [], []
        for d, v in zip(image_docs, image_vecs):
            if v is None:
                continue
            ok_texts.append(d.page_content)
            ok_vecs.append(v)
            ok_metas.append(d.metadata)
        if ok_vecs:
            vs.add_embeddings(
                texts=ok_texts,
                embeddings=ok_vecs,
                metadatas=ok_metas,
            )
        indexed_images = len(ok_vecs)
        skipped = len(image_docs) - indexed_images
        msg = f"  Indexed {indexed_images} image chunks"
        if skipped:
            msg += f" ({skipped} skipped — unreachable URL)"
        print(msg)

    total = len(text_docs) + indexed_images
    print(f"Collection '{collection_name}' ready — {total} chunks "
          f"({len(text_docs)} text + {indexed_images} image).")
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

        video_urls = doc.metadata.get("video_urls") or []
        video_line = f"\nVideo URL(s): {', '.join(video_urls)}" if video_urls else ""

        context_parts.append(
            f"[{citation}] {label} ({source})\n{snippet}{video_line}\n{SEPARATOR}"
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
            "ref":        i,
            "source":     source,
            "title":      meta.get("title", Path(source).stem),
            "module":     module,
            "course":     meta.get("course", ""),
            "course_id":  meta.get("course_id", ""),
            "content":    doc.page_content[:800].strip(),
            "video_urls": list(meta.get("video_urls") or []),
        })

    return refs
