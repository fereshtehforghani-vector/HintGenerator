"""
Document loaders for the ZebraBot RAG knowledge base.

On GCP, call download_gcs_documents() first to populate /tmp,
then call load_all_documents() to get chunked LangChain Documents.

Local usage (for testing):
    docs = load_all_documents(
        lms_dir=Path("..."),
        libraries_pdf=Path("..."),
        mistakes_docx=Path("..."),
    )
"""

import re
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document as LCDoc
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import (
    Language,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from docx import Document


# ── LMS content cleaning & image extraction ───────────────────────────────────
# Per-course filter for which `![alt](url)` images are worth embedding. Alt
# text is matched case-insensitively and ignores trailing whitespace. Everything
# else (decorative images like `![camel]`, `![truck]`, random screenshots) is
# stripped along with all other links.
_LMS_IMAGE_ALT_PATTERNS: dict[str, re.Pattern] = {
    "sdv":              re.compile(r"^\s*image\s*$", re.IGNORECASE),
    "reactive_robtics": re.compile(
        r"^\s*(code|coding screen|mblox|myblock code)\s*$", re.IGNORECASE
    ),
}

_MD_IMAGE_RE     = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK_RE      = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FRONTMATTER_RE  = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)

# `[Video: Video](url)` lines in LMS markdown point at the flipbook / vimeo
# asset for a section. Preserve them through cleaning+chunking as a
# placeholder, then lift them into chunk metadata so the LLM can cite them.
_VIDEO_LINK_RE        = re.compile(r"\[Video:\s*Video\]\((\S+?)\)")
_VIDEO_PLACEHOLDER_RE = re.compile(r"\[\[VIDEO_URL::(.+?)\]\]")


def _extract_image_docs(
    body: str,
    lesson_meta: dict,
    course_id: str,
) -> list[LCDoc]:
    """Return one LCDoc per qualifying `![alt](url)` in the body.

    The ``page_content`` is the alt text (not used for embedding — the image
    bytes are embedded by ``GeminiEmbedding2.embed_images``). The image URL
    is stored both as ``source`` so the front-end can link to it as a
    reference, and as ``image_url`` to make the intent explicit.
    """
    pattern = _LMS_IMAGE_ALT_PATTERNS.get(course_id)
    if not pattern:
        return []
    docs: list[LCDoc] = []
    seen: set[str] = set()
    for alt, url in _MD_IMAGE_RE.findall(body):
        if not pattern.match(alt):
            continue
        if url in seen:
            continue
        seen.add(url)
        meta = dict(lesson_meta)
        meta.update({
            "source":        url,
            "image_url":     url,
            "is_image":      True,
            "modality":      "image",
            "parent_source": lesson_meta.get("source", ""),
            "alt":           alt.strip(),
        })
        docs.append(LCDoc(page_content=alt.strip() or "image", metadata=meta))
    return docs


def _clean_lms_body(body: str) -> str:
    """Strip HTML comments and all markdown links/images from LMS text so
    chunks contain only course material. `[Video: Video](url)` links are
    rewritten to a `[[VIDEO_URL::url]]` placeholder that survives the
    generic link strip; `chunk_lms_docs` lifts it into metadata."""
    body = _HTML_COMMENT_RE.sub("", body)
    body = _MD_IMAGE_RE.sub("", body)
    body = _VIDEO_LINK_RE.sub(
        lambda m: f"\n[[VIDEO_URL::{m.group(1).strip()}]]\n", body
    )
    body = _MD_LINK_RE.sub("", body)
    # Collapse runs of blank lines produced by the removals.
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


# ── GCS download ───────────────────────────────────────────────────────────────
def download_gcs_documents(bucket_name: str, tmp_dir: str = "/tmp") -> dict[str, Path]:
    """
    Download all RAG source documents from GCS to the Cloud Function's /tmp.

    Returns a dict of { label: local_path }.
    """
    from google.cloud import storage

    client  = storage.Client()
    bucket  = client.bucket(bucket_name)
    tmp     = Path(tmp_dir)
    paths: dict[str, Path] = {}

    # Single files. libraries.pdf is required; M1.docx is optional — skip if
    # the bucket doesn't carry it (current state) instead of failing the
    # whole build on a 404.
    for blob_name, label, required in [
        ("libraries.pdf", "libraries_pdf", True),
        ("M1.docx",       "mistakes_docx", False),
    ]:
        blob = bucket.blob(blob_name)
        if not blob.exists():
            if required:
                raise FileNotFoundError(f"Required blob gs://{bucket_name}/{blob_name} not found")
            print(f"  Skipping optional blob (not in bucket): {blob_name}")
            continue
        dest = tmp / blob_name
        blob.download_to_filename(str(dest))
        paths[label] = dest
        print(f"  Downloaded {blob_name} -> {dest}")

    # LMS folder (all .md files under LMS/)
    lms_dir = tmp / "LMS"
    lms_dir.mkdir(exist_ok=True)
    for blob in client.list_blobs(bucket_name, prefix="LMS/"):
        if blob.name.endswith("/"):
            continue
        rel  = blob.name[len("LMS/"):]
        dest = lms_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
    paths["lms_dir"] = lms_dir
    print(f"  Downloaded LMS/ -> {lms_dir}")

    # ZebraBot firmware (optional — only if present in bucket)
    zebrabot_dir = tmp / "zebrabot"
    zebrabot_dir.mkdir(exist_ok=True)
    blobs_found = 0
    for blob in client.list_blobs(bucket_name, prefix="zebrabot/"):
        if blob.name.endswith("/"):
            continue
        rel  = blob.name[len("zebrabot/"):]
        dest = zebrabot_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        blobs_found += 1
    if blobs_found:
        paths["zebrabot_dir"] = zebrabot_dir
        print(f"  Downloaded zebrabot/ -> {zebrabot_dir} ({blobs_found} files)")

    return paths


# ── Individual loaders ─────────────────────────────────────────────────────────
def load_lms_docs(lms_dir: Path, source_url_prefix: Optional[str] = None) -> list[LCDoc]:
    """Load all .md curriculum files from the LMS_PARSED directory.

    Each document gets a ``course_id`` metadata field derived from its
    immediate parent directory name by stripping the ``rag_output_`` prefix
    (e.g. ``rag_output_sdv`` → ``sdv``).  This is the stable key used to
    filter the vector store at query time so that retrieval can be scoped
    to a single course.

    If ``source_url_prefix`` is given, the ``source`` metadata becomes a
    clickable URL built as ``{prefix}/{path_relative_to_lms_dir}`` — this is
    how GCP runs turn ``/tmp/LMS/...`` into a ``storage.cloud.google.com``
    link. When omitted, ``source`` falls back to the local filesystem path.

    Returns a flat list of LCDocs containing:
      * One *text* doc per lesson, with frontmatter, HTML comments, and all
        markdown links/images stripped — leaving only course material.
      * Zero or more *image* docs (``metadata["is_image"] == True``) for
        images whose alt text matches the course's filter (see
        ``_LMS_IMAGE_ALT_PATTERNS``). Image docs carry the image URL in
        ``source`` / ``image_url`` so they can be embedded multimodally and
        cited as clickable references at query time.
    """
    docs: list[LCDoc] = []
    image_count = 0
    prefix = source_url_prefix.rstrip("/") if source_url_prefix else None
    for md_file in sorted(lms_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        # Strip the "rag_output_" prefix so the id is clean: "sdv", "reactive_robtics", etc.
        dir_name  = md_file.parent.name
        course_id = dir_name.removeprefix("rag_output_")
        if prefix:
            rel    = md_file.relative_to(lms_dir).as_posix()
            source = f"{prefix}/{rel}"
        else:
            source = str(md_file)
        meta = {
            "source":    source,
            "type":      "curriculum",
            "course_id": course_id,
            "modality":  "text",
        }

        # Parse frontmatter into metadata and drop it from the body.
        body = text
        fm = _FRONTMATTER_RE.match(text)
        if fm:
            for line in fm.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            body = text[fm.end():]

        # Extract qualifying images BEFORE cleaning removes the markdown.
        img_docs = _extract_image_docs(body, meta, course_id)
        docs.extend(img_docs)
        image_count += len(img_docs)

        # Text chunk gets cleaned: no links, no HTML comments, no frontmatter.
        cleaned = _clean_lms_body(body)
        if cleaned:
            docs.append(LCDoc(page_content=cleaned, metadata=meta))
    print(f"  LMS docs loaded: {len(docs) - image_count} text + {image_count} image")
    return docs


def load_libraries_pdf(pdf_path: Path) -> list[LCDoc]:
    """Load the Z-Bot C++ library reference PDF."""
    pages = PyPDFLoader(str(pdf_path)).load()
    for p in pages:
        p.metadata.update({
            "type":     "library_reference",
            "source":   str(pdf_path),
            "modality": "text",
        })
    print(f"  libraries.pdf pages loaded: {len(pages)}")
    return pages


def load_mistakes_docx(docx_path: Path) -> list[LCDoc]:
    """Parse M1.docx into per-section mistake-pattern Documents."""
    doc = Document(str(docx_path))
    chunks, current_section, current_text = [], "General", []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if para.style.name.startswith("Heading"):
            if current_text:
                chunks.append(LCDoc(
                    page_content="\n".join(current_text),
                    metadata={"source": str(docx_path), "type": "mistake_pattern",
                              "section": current_section, "modality": "text"},
                ))
            current_section, current_text = text, [text]
        else:
            current_text.append(text)
    if current_text:
        chunks.append(LCDoc(
            page_content="\n".join(current_text),
            metadata={"source": str(docx_path), "type": "mistake_pattern",
                      "section": current_section, "modality": "text"},
        ))
    print(f"  Mistakes docx chunks loaded: {len(chunks)}")
    return chunks


def load_zebrabot_source(zebrabot_dir: Path) -> list[LCDoc]:
    """Load ZebraBot firmware headers and examples."""
    if not zebrabot_dir.exists():
        print(f"  ZebraBot source dir not found, skipping: {zebrabot_dir}")
        return []
    patterns = [
        ("lib/**/src/*.h", "zebrabot_library"),
        ("examples/*.cpp", "zebrabot_example"),
        ("src/*.cpp",      "zebrabot_source"),
        ("test/*.cpp",     "zebrabot_test"),
    ]
    docs = []
    for glob_pat, doc_type in patterns:
        for fpath in sorted(zebrabot_dir.glob(glob_pat)):
            if ".pio" in fpath.parts:
                continue
            code = fpath.read_text(encoding="utf-8", errors="replace")
            docs.append(LCDoc(
                page_content=f"// FILE: {fpath.name}  (type: {doc_type})\n{code}",
                metadata={"source": str(fpath), "type": doc_type,
                          "filename": fpath.name, "project": "zebrabot_V18",
                          "modality": "text"},
            ))
    print(f"  ZebraBot source files loaded: {len(docs)}")
    return docs


# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_lms_docs(docs: list[LCDoc]) -> list[LCDoc]:
    """
    Split curriculum markdown files on header boundaries first, then apply a
    secondary character split to keep each chunk within ~1000 chars.

    Header metadata (h1/h2/h3) is merged into the chunk so the LLM receives
    section context even when a chunk starts mid-section.
    """
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,   # keep header text in the chunk content
    )
    # Secondary splitter for sections that exceed the size limit
    fallback = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=120,
    )

    chunks: list[LCDoc] = []
    for doc in docs:
        # Image docs are embedded as a single unit (the image itself) — don't
        # run them through the text splitter.
        if doc.metadata.get("is_image"):
            chunks.append(doc)
            continue
        for md_chunk in md_splitter.split_text(doc.page_content):
            # Merge original metadata (source, course_id, type, …) with
            # the header metadata added by MarkdownHeaderTextSplitter
            merged = LCDoc(
                page_content=md_chunk.page_content,
                metadata={**doc.metadata, **md_chunk.metadata},
            )
            for sub in fallback.split_documents([merged]):
                urls = _VIDEO_PLACEHOLDER_RE.findall(sub.page_content)
                if urls:
                    seen: set[str] = set()
                    sub.metadata["video_urls"] = [
                        u for u in urls if not (u in seen or seen.add(u))
                    ]
                    sub.page_content = _VIDEO_PLACEHOLDER_RE.sub("", sub.page_content)
                    sub.page_content = re.sub(r"\n{3,}", "\n\n", sub.page_content).strip()
                chunks.append(sub)

    print(f"  LMS chunks after markdown split: {len(chunks)}")
    return chunks


def chunk_library_docs(docs: list[LCDoc]) -> list[LCDoc]:
    """Split library PDF pages with a standard recursive character splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)


def chunk_zebrabot_docs(docs: list[LCDoc]) -> list[LCDoc]:
    """
    Split ZebraBot C++ source using C++-aware separators so function and
    class boundaries are preferred split points over arbitrary character counts.
    """
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.CPP,
        chunk_size=1000,
        chunk_overlap=100,
    )
    return splitter.split_documents(docs)


# ── Combined pipeline ──────────────────────────────────────────────────────────
def load_all_documents(
    lms_dir: Path,
    libraries_pdf: Path,
    mistakes_docx: Optional[Path] = None,
    zebrabot_dir: Optional[Path] = None,
    lms_source_url_prefix: Optional[str] = None,
) -> list[LCDoc]:
    """Load and chunk all knowledge-base documents, using a chunking strategy
    appropriate for each document type."""
    chunks: list[LCDoc] = []

    chunks += chunk_lms_docs(load_lms_docs(lms_dir, source_url_prefix=lms_source_url_prefix))
    chunks += chunk_library_docs(load_libraries_pdf(libraries_pdf))
    if mistakes_docx:
        # Mistake patterns are already split per section by the loader
        chunks += load_mistakes_docx(mistakes_docx)
    if zebrabot_dir:
        chunks += chunk_zebrabot_docs(load_zebrabot_source(zebrabot_dir))

    print(f"  Total chunks: {len(chunks)}")
    return chunks
