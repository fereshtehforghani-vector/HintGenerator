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

    # Single files
    for blob_name, label in [
        ("libraries.pdf", "libraries_pdf"),
        ("M1.docx",       "mistakes_docx"),
    ]:
        dest = tmp / blob_name
        bucket.blob(blob_name).download_to_filename(str(dest))
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
def load_lms_docs(lms_dir: Path) -> list[LCDoc]:
    """Load all .md curriculum files from the LMS_PARSED directory.

    Each document gets a ``course_id`` metadata field derived from its
    immediate parent directory name by stripping the ``rag_output_`` prefix
    (e.g. ``rag_output_sdv`` → ``sdv``).  This is the stable key used to
    filter the vector store at query time so that retrieval can be scoped
    to a single course.
    """
    docs = []
    for md_file in sorted(lms_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        # Strip the "rag_output_" prefix so the id is clean: "sdv", "reactive_robtics", etc.
        dir_name  = md_file.parent.name
        course_id = dir_name.removeprefix("rag_output_")
        meta = {"source": str(md_file), "type": "curriculum", "course_id": course_id}
        fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm:
            for line in fm.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
        docs.append(LCDoc(page_content=text, metadata=meta))
    print(f"  LMS docs loaded: {len(docs)}")
    return docs


def load_libraries_pdf(pdf_path: Path) -> list[LCDoc]:
    """Load the Z-Bot C++ library reference PDF."""
    pages = PyPDFLoader(str(pdf_path)).load()
    for p in pages:
        p.metadata.update({"type": "library_reference", "source": str(pdf_path)})
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
                              "section": current_section},
                ))
            current_section, current_text = text, [text]
        else:
            current_text.append(text)
    if current_text:
        chunks.append(LCDoc(
            page_content="\n".join(current_text),
            metadata={"source": str(docx_path), "type": "mistake_pattern",
                      "section": current_section},
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
                          "filename": fpath.name, "project": "zebrabot_V18"},
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
        for md_chunk in md_splitter.split_text(doc.page_content):
            # Merge original metadata (source, course_id, type, …) with
            # the header metadata added by MarkdownHeaderTextSplitter
            merged = LCDoc(
                page_content=md_chunk.page_content,
                metadata={**doc.metadata, **md_chunk.metadata},
            )
            chunks.extend(fallback.split_documents([merged]))

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
) -> list[LCDoc]:
    """Load and chunk all knowledge-base documents, using a chunking strategy
    appropriate for each document type."""
    chunks: list[LCDoc] = []

    chunks += chunk_lms_docs(load_lms_docs(lms_dir))
    chunks += chunk_library_docs(load_libraries_pdf(libraries_pdf))
    if mistakes_docx:
        # Mistake patterns are already split per section by the loader
        chunks += load_mistakes_docx(mistakes_docx)
    if zebrabot_dir:
        chunks += chunk_zebrabot_docs(load_zebrabot_source(zebrabot_dir))

    print(f"  Total chunks: {len(chunks)}")
    return chunks
