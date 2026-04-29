# Zebra Hint Generator — RAG Design Documentation

This document describes the end-to-end design of the Retrieval-Augmented
Generation (RAG) system that powers the Socratic tutor in
[zebra-hint-generator/](.). It covers the database schema, source documents,
chunking strategies for each modality, image handling, embedding model, and
the exact retrieval path executed when a student submits a question.

Code references throughout point to the canonical source files:
[shared/data_loaders.py](shared/data_loaders.py),
[shared/rag_utils.py](shared/rag_utils.py),
[shared/tutor.py](shared/tutor.py),
[shared/config.py](shared/config.py),
[build_rag/main.py](build_rag/main.py),
[query_rag/main.py](query_rag/main.py).

---

## 1. High-level architecture

Two independent Cloud Run services share a `shared/` Python package and a
single Cloud SQL Postgres instance with the `pgvector` extension enabled.

| Service | Path | Role |
|---|---|---|
| `build-rag-database` | [build_rag/main.py](build_rag/main.py) | Reads source docs from GCS, chunks, embeds, writes vectors to Postgres. Triggered on demand (HTTP POST or Eventarc on the LMS bucket). |
| `query-rag` | [query_rag/main.py](query_rag/main.py) | Receives a student's code/question/image, runs retrieval, builds prompt, calls LLM, returns Socratic hint + lesson references. |

Both services connect to the same database/collection via constants in
[shared/config.py:13-22](shared/config.py#L13-L22):

```python
GCP_PROJECT_ID            = "zebra-ai-assist-poc"
INSTANCE_CONNECTION_NAME  = "zebra-ai-assist-poc:us-central1:zebra-robotics-convo-history"
DB_NAME                   = "zebra_db"
COLLECTION_NAME           = "zbot_rag_gcp"
EMBEDDING_DIM             = 3072       # Gemini Embedding 2 output dim
BUCKET_NAME               = "zebra-rag-documents"
```

---

## 2. Database schema

The vector store is `langchain-postgres`'s `PGVector`, which lays out two
tables in the `zebra_db` database (both auto-created the first time
`PGVector.create_collection()` runs).

### 2.1 `langchain_pg_collection`

One row per logical collection. We use a single collection: `zbot_rag_gcp`.

| Column | Type | Description |
|---|---|---|
| `uuid` | `uuid` (PK) | Collection identifier referenced by the embeddings table. |
| `name` | `text` | Human-readable collection name (`zbot_rag_gcp`). |
| `cmetadata` | `jsonb` | Free-form collection metadata (unused). |

### 2.2 `langchain_pg_embedding`

One row per indexed chunk (text **or** image). Currently 416 rows
(325 text + 91 image — see
[DEPLOYMENT_NOTES.md](DEPLOYMENT_NOTES.md#current-state)).

| Column | Type | Description |
|---|---|---|
| `id` | `text` (PK) | Per-chunk UUID. |
| `collection_id` | `uuid` (FK → `langchain_pg_collection.uuid`) | Link to the parent collection. |
| `embedding` | `vector(3072)` | The Gemini Embedding 2 vector for this chunk. |
| `document` | `text` | The chunk's textual content. For image chunks this is the alt text only — the embedded vector comes from the image bytes, not from `document`. |
| `cmetadata` | `jsonb` | Per-chunk metadata (filtered against at query time via PGVector's JSONB filter). See §2.3. |

`use_jsonb=True` is set when constructing `PGVector` so the metadata column
is JSONB rather than the legacy keyed metadata table — this is what allows
the `course_id` pre-filter at query time. See
[shared/rag_utils.py:143-150](shared/rag_utils.py#L143-L150).

### 2.3 Per-chunk metadata (`cmetadata` JSONB)

Set during loading and chunking. Keys vary by document type:

| Key | Set by | Values |
|---|---|---|
| `source` | all loaders | A clickable HTTPS URL for production builds (GCS for curriculum/library, CloudFront for images), or the local file path for local dev builds. |
| `type` | all loaders | One of `curriculum`, `library_reference`, `mistake_pattern`, `zebrabot_library`, `zebrabot_example`, `zebrabot_source`, `zebrabot_test`. Drives label + citation namespace at query time. |
| `modality` | all loaders | `text` or `image`. |
| `course_id` | LMS loader | LMS subdirectory name with `rag_output_` stripped. Today: `sdv` or `reactive_robtics` (note typo — it matches the directory name on disk). Used as the retrieval filter key. |
| `is_image` | LMS image extractor | `True` for image rows, absent otherwise. Used to route through the image embedding path during build, and to skip the markdown chunker. |
| `image_url`, `parent_source`, `alt` | LMS image extractor | Image URL (duplicated as `source`), the lesson the image came from, and the alt text. |
| `h1`, `h2`, `h3` | LMS markdown header splitter | Heading text at each level so chunks carry section context even when a chunk starts mid-section. |
| `title`, `module`, `course` | LMS frontmatter parser | Pulled from each `.md` file's YAML frontmatter; surfaced in `lms_references` for the frontend. |
| `video_urls` | LMS chunker | List of video URLs lifted from `[Video: Video](...)` markers found inside the chunk. Surfaced to the LLM and to `lms_references`. |
| `section` | mistakes loader | The Heading-styled paragraph that introduced the section. |
| `filename`, `project` | firmware loader | C++ source filename and `project="zebrabot_V18"`. |

There are two other supporting tables that live in the same database but
are **not part of the RAG**:
`prompt_config` (system-prompt fragments loaded by
[shared/tutor.py:28-57](shared/tutor.py#L28-L57)),
`students` (per-student profile and turn counter), and
`conversation_history` (logging — see
[shared/conversation_store.py](shared/conversation_store.py)).

---

## 3. Source documents

All source documents live in `gs://zebra-rag-documents/` and are downloaded
to `/tmp` at build time by
[`download_gcs_documents()`](shared/data_loaders.py#L107-L167).

| Location in bucket | Loader | Type tag | Notes |
|---|---|---|---|
| `LMS/LMS_PARSED/<course>/*.md` | [`load_lms_docs`](shared/data_loaders.py#L171-L234) | `curriculum` (text) + image rows | Markdown lessons with YAML frontmatter; per-course image filtering applied. |
| `libraries.pdf` | [`load_libraries_pdf`](shared/data_loaders.py#L237-L247) | `library_reference` | Z-Bot C++ library reference — required. |
| `zebrabot/lib/**/src/*.h`, `examples/*.cpp`, `src/*.cpp`, `test/*.cpp` (optional) | [`load_zebrabot_source`](shared/data_loaders.py#L278-L302) | `zebrabot_library` / `_example` / `_source` / `_test` | ZebraBot V18 firmware source. |

LMS courses on disk today: `sdv` (Self-Driving Car) and `reactive_robtics`
(Reactive Robotics — keep the typo, it is the directory name).

---

## 4. Chunking strategy

Different document types use different chunkers. Top-level orchestration is
[`load_all_documents()`](shared/data_loaders.py#L377-L397).

### 4.1 LMS markdown — [`chunk_lms_docs`](shared/data_loaders.py#L306-L350)

Two-stage split:

1. **Header split** with `MarkdownHeaderTextSplitter` on `#`, `##`, `###`.
   `strip_headers=False` so the heading text stays inside the chunk.
   Heading metadata (`h1` / `h2` / `h3`) is merged into the chunk's
   `cmetadata` so a chunk that starts mid-section still carries its parent
   section's context.
2. **Character split** with `RecursiveCharacterTextSplitter`,
   `chunk_size=1000`, `chunk_overlap=120`, applied to any header section
   that exceeded 1000 chars.

Pre-processing run by [`_clean_lms_body`](shared/data_loaders.py#L90-L103) before chunking:

- YAML frontmatter is parsed into metadata, then stripped from the body.
- HTML comments (`<!-- ... -->`) are removed.
- All markdown image links are removed (qualifying images are extracted as
  separate chunks first — see §5).
- All other markdown links are removed.
- `[Video: Video](url)` links are rewritten to a `[[VIDEO_URL::url]]`
  placeholder so the URL survives the link strip; after the recursive
  character split, [`chunk_lms_docs`](shared/data_loaders.py#L339-L346)
  lifts the placeholder out into the chunk's `video_urls` metadata and
  removes it from the visible text.

Image chunks bypass the markdown splitter — they are appended to the chunk
list as-is so a single embedding represents the whole image
([data_loaders.py:328-330](shared/data_loaders.py#L328-L330)).

### 4.2 Library PDF — [`chunk_library_docs`](shared/data_loaders.py#L353-L360)

`PyPDFLoader` produces one Document per page; then a generic
`RecursiveCharacterTextSplitter` with `chunk_size=1000`, `chunk_overlap=120`,
splitting preferentially on `\n\n`, then `\n`, then space, then character.

### 4.4 ZebraBot firmware — [`chunk_zebrabot_docs`](shared/data_loaders.py#L363-L373)

`RecursiveCharacterTextSplitter.from_language(Language.CPP, chunk_size=1000,
chunk_overlap=100)` so function and class boundaries are preferred split
points over arbitrary character counts.

---

## 5. Image handling

Curriculum lessons embed inline diagrams (`![alt](url)`). Most are
decorative (mascots, photos), but a curated set of diagrams is
educationally useful and gets embedded multimodally.

### 5.1 Selection (which images get indexed)

[`_LMS_IMAGE_ALT_PATTERNS`](shared/data_loaders.py#L35-L40) keeps a
per-course allow-list keyed off the markdown `alt` text:

| Course | Allowed alt patterns |
|---|---|
| `sdv` | `image` |
| `reactive_robtics` | `code`, `coding screen`, `mblox`, `myblock code` |

Anything that does not match (`![camel]`, `![truck]`, screenshots) is
stripped along with all other links and never reaches the index.
Duplicate URLs within one lesson are deduplicated.

### 5.2 Per-image chunk construction

[`_extract_image_docs`](shared/data_loaders.py#L54-L87) emits one
`LangChain Document` per qualifying image with:

- `page_content` = the alt text (or `"image"` if blank). This is **only**
  stored as the chunk's text — it is not what the embedding sees.
- `metadata.source` = the image URL (so the frontend can render it as a
  clickable reference link).
- `metadata.image_url` = same URL, made explicit.
- `metadata.is_image` = `True`, `modality` = `"image"`.
- `metadata.parent_source` = the lesson the image came from.
- All other lesson metadata (`course_id`, frontmatter `title` / `module`,
  etc.) inherited from the parent lesson.

### 5.3 Multimodal embedding — [`GeminiEmbedding2.embed_images`](shared/rag_utils.py#L77-L107)

For each image URL:

1. Fetch the bytes via [`_download_image`](shared/rag_utils.py#L116-L139).
   GCS URLs (`storage.cloud.google.com` / `storage.googleapis.com`) go
   through the authenticated `google-cloud-storage` client so private
   buckets work; everything else uses plain HTTP with a custom UA string.
2. Wrap as a `google.genai.types.Part.from_bytes(data, mime_type)` and
   call `embed_content` on `gemini-embedding-2-preview`.
3. Sleep 0.5s between calls to stay under per-minute quotas.
4. Failures (404/403 on dead asset URLs) are logged and yield `None` in the
   parallel result list — the caller skips those entries instead of
   aborting the whole build. See
   [`rebuild_vectorstore`](shared/rag_utils.py#L218-L238).

### 5.4 Storage path for image chunks

Image chunks bypass the standard `add_documents` path because their
vectors are already computed.
[`rebuild_vectorstore`](shared/rag_utils.py#L201-L238) calls
`vs.add_embeddings(texts=..., embeddings=..., metadatas=...)` so the
precomputed image vectors land in `langchain_pg_embedding` alongside the
text chunks, in the same collection, in the same vector space.

This works because `gemini-embedding-2-preview` produces 3072-d vectors
for both text and image inputs — text and image embeddings are directly
comparable under cosine similarity.

---

## 6. Embedding model

[`GeminiEmbedding2`](shared/rag_utils.py#L26-L107) wraps Google's
`gemini-embedding-2-preview` (3072 dimensions) as a LangChain `Embeddings`
implementation.

Key behaviours:

- **One call per text.** The Gemini SDK treats `contents=[t1, t2, ...]` as
  parts of one document and returns a single combined embedding, so
  [`_embed_batch`](shared/rag_utils.py#L56-L64) loops one-text-at-a-time
  to get one embedding per chunk.
- **Outer batching for rate limits.** `embed_documents` walks `texts` in
  groups of `batch_size=20` (default) and sleeps 1s between groups.
- **Retry on 429.** [`_call_with_retry`](shared/rag_utils.py#L42-L54) does
  up to 5 exponential backoff retries on `RESOURCE_EXHAUSTED`.
- **Dimension is locked into the schema.** `langchain_pg_embedding.embedding`
  is `vector(3072)`. If the embedding model is ever swapped, both
  `langchain_pg_embedding` and `langchain_pg_collection` must be dropped
  first or LangChain will refuse to insert vectors of the new dimension.

---

## 7. Build pipeline (end-to-end)

Triggered by an HTTP POST to `build-rag-database`. Walks through
[build_rag/main.py:34-121](build_rag/main.py#L34-L121).

1. **Eventarc filter** — if the request was triggered by a GCS object
   change outside `LMS/LMS_PARSED/`, return early without rebuilding
   (avoids burning quota on irrelevant bucket activity).
2. **Hydrate secrets** from Secret Manager into `os.environ`
   (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, DB password).
3. **Download** all source docs from `gs://zebra-rag-documents/` into
   `/tmp` ([`download_gcs_documents`](shared/data_loaders.py#L107-L167)).
4. **Load + chunk** via [`load_all_documents`](shared/data_loaders.py#L377-L397).
   The LMS loader is invoked with
   `lms_source_url_prefix="https://storage.cloud.google.com/zebra-rag-documents/LMS"`
   so each curriculum chunk's `source` is a clickable HTTPS URL, not a
   `/tmp/...` path. Library chunks have their `source` rewritten to a GCS
   URL after loading ([build_rag/main.py:86-89](build_rag/main.py#L86-L89)).
5. **Optional dry-run** — if the request body is `{"dry_run": true}`,
   return chunk count and skip the embedding step.
6. **Connect to Cloud SQL** via the Cloud SQL Python Connector +
   `pg8000`.
7. **Drop & recreate the collection** in PGVector, then call
   [`rebuild_vectorstore`](shared/rag_utils.py#L180-L243):
   - Text chunks indexed in batches of 20 via `vs.add_documents`
     (LangChain calls `embed_documents` under the hood).
   - Image chunks embedded multimodally via `embed_images`, then inserted
     via `vs.add_embeddings` with the precomputed vectors. Failed fetches
     are dropped and reported.
8. Return `{"status": "success", "chunks_indexed": N}`.

---

## 8. Query pipeline (top-10 retrieval, end-to-end)

Triggered by an HTTP POST to `query-rag`. Walks through
[query_rag/main.py:92-166](query_rag/main.py#L92-L166).

### 8.1 Request parsing

Either `application/json` or `multipart/form-data`. Fields: `query` /
`question`, `code`, `provider`, `course_id`, `conversation_id`,
`student_id`. Multipart can include an image (PNG/JPG/JPEG/WEBP) or a
`.cpp` file ([shared/file_handler.py](shared/file_handler.py)). Image
uploads are sent to `gs://zebra-robotics-images/` and a signed URL is
returned to the client.

### 8.2 Warm-up cache

Module-level globals `_engine` and `_vectorstore` are populated on the
first request and reused for the lifetime of the container instance —
this avoids paying the Secret Manager + DB connection cost on every
request ([query_rag/main.py:48-63](query_rag/main.py#L48-L63)).

### 8.3 Retriever construction — [`get_retriever`](shared/rag_utils.py#L153-L177)

```python
retriever = get_retriever(vs, top_k=10, course_id=course_id)
```

When `course_id` is supplied, the retriever attaches a PGVector metadata
pre-filter:

```json
{ "$or": [
    { "course_id": { "$eq": "<course_id>" } },
    { "type":      { "$ne": "curriculum"  } }
] }
```

Effect: curriculum chunks are filtered to the requested course only;
**non-curriculum chunks (library docs, mistake patterns, firmware) are
always searched regardless of course.** The filter is translated by
LangChain into a `WHERE (cmetadata->>'course_id' = ...) OR
(cmetadata->>'type' != 'curriculum')` clause executed by Postgres before
the ANN search.

### 8.4 The retrieval call itself

Inside [`build_rag_context`](shared/rag_utils.py#L247-L319):

```python
docs = retriever.invoke(query)   # query = student_code + "\n" + question
```

What this triggers:

1. **Embed the query.** `GeminiEmbedding2.embed_query(query)` →
   one 3072-d vector via `gemini-embedding-2-preview`.
2. **Postgres ANN search.** PGVector executes a single SQL query
   equivalent to:
   ```sql
   SELECT id, document, cmetadata, embedding <=> %s AS distance
     FROM langchain_pg_embedding
    WHERE collection_id = %s
      AND <metadata pre-filter from §8.3>
    ORDER BY embedding <=> %s
    LIMIT 10;
   ```
   `<=>` is pgvector's cosine-distance operator. The two `%s` vector
   placeholders are the same query embedding. The result is the 10
   chunks with the smallest cosine distance to the query — text and
   image chunks compete in the same vector space.
3. **Return.** LangChain wraps each result as a `Document` whose
   `page_content` is the `document` column and `metadata` is the
   `cmetadata` JSON.

There is no re-ranker; top-10 by raw cosine distance is the final ordering.

### 8.5 Context assembly — [`build_rag_context`](shared/rag_utils.py#L247-L319)

The 10 retrieved docs are reordered and renumbered to satisfy the
citation contract that the validator and the frontend rely on:

1. **Curriculum chunks first**, deduplicated by `source` so each LMS
   lesson appears at most once. The first (highest-relevance) chunk per
   lesson wins. This dedup is what keeps the `[N]` citations gap-free
   and aligned with the `lms_references` array the frontend renders.
2. **Non-curriculum chunks** (library, mistake, firmware) follow, no
   dedup, in retrieval order.
3. Each chunk is rendered as a numbered, labeled context block:

   ```text
   [1] 📘 Curriculum (lesson_filename.md)
   <up to 1200 chars of cleaned chunk text>
   Video URL(s): https://...   ← only if the chunk had video links
   ──────────────────────────────────────────────────
   ```

   Curriculum chunks get integer citations `[1]`, `[2]`, …; everything
   else gets prefixed citations `[L1]`, `[L2]`, … so the two namespaces
   never collide.

### 8.6 Reference list — [`extract_lms_references`](shared/rag_utils.py#L322-L365)

In parallel, one entry per unique LMS lesson is emitted with a `ref`
field equal to the `[N]` number the LLM will see. The frontend uses
this to turn `According to [2]…` into a clickable lesson card.

### 8.7 Prompt assembly + LLM call

[`AgenticTutor.analyse_code`](shared/tutor.py#L244-L276):

- System prompt is composed once at construction time from
  `prompt_config` rows (`ROLE` → `SOCRATIC_CONSTRAINT` →
  `SAFETY_AND_SCOPE` → `ENCOURAGEMENT_POLICY`), the kid-safe appendix,
  the per-student profile block, and the per-track behavior block.
- User prompt is built by
  [`format_user_prompt`](shared/tutor.py#L123-L168): student code +
  retrieved context + escalation instruction (broad → specific →
  near-direct scaffold based on `MAX_TURNS=5` minus turns used so far) +
  citation rules.
- Sent to the configured provider via
  [`LLMInterface.chat`](shared/llm_interface.py).

### 8.8 Output validation

[`validate_and_sanitize_model_output`](shared/security.py) requires:

- At least one `[N]` or `[LN]` citation, AND
- Four section markers: `Mistake Type`, `Hint`, `Guiding Question`,
  `Curriculum Reference`.

If either fails, `build_security_fallback` returns a canned safe message
and an empty `lms_references` list.

### 8.9 Response

```json
{
  "response":        "...Socratic markdown with [1]/[L2] citations...",
  "lms_references":  [{ "ref": 1, "title": "...", "module": 7,
                         "course_id": "sdv", "video_urls": [...] }, ...],
  "conversation_id": "<echoed>",
  "stored_file_url": "<signed GCS URL or null>"
}
```

The response body is streamed back as `text/plain` in 20-character
chunks so the UI can render it word-by-word; the JSON `lms_references`
ride along in the `X-LMS-References` response header.

---

## 9. Image-input query path

[`AgenticTutor.analyse_image`](shared/tutor.py#L278-L308) reuses the same
text retriever — the student-uploaded image is **not** embedded for
retrieval. Instead, the question text (or the literal string
`"spike block code program"` if no question was asked) is what
`build_rag_context` retrieves against. The image bytes are then passed
to the multimodal LLM (`LLMInterface.chat_with_image`) alongside the
text retrieved context and the
[`format_image_prompt`](shared/tutor.py#L171-L197) instructions.

This is asymmetric on purpose: the retrieval index contains *curriculum
diagrams* (multimodal embeddings of LMS images) so they can surface for
text queries about a concept; we have not yet wired the *student image*
through the embedding path.

---

## 10. Knobs that are easy to break (read this before changing things)

| Change | Consequence |
|---|---|
| Reorder chunks in `build_rag_context` after the curriculum-first dedup | `lms_references[].ref` numbers desync from the LLM's `[N]` citations — frontend links go to the wrong lesson. |
| Swap embedding model without dropping `langchain_pg_embedding` and `langchain_pg_collection` | Vector dimension mismatch at insert time; build fails. |
| Edit section header strings in `SOCRATIC_SYSTEM_PROMPT` (`Mistake Type`, etc.) | Output validator rejects every response → users see only the safe fallback. |
| Index `[1] ... [10]` citation namespace overlapping with non-curriculum citations | Citation collisions; frontend can't resolve which `[2]` is which — keep curriculum on `[N]` and the rest on `[LN]`. |
| Change `top_k` away from 10 | Allowed, but verify the frontend still gets enough lesson links and the prompt still fits the model's context window. |
| Move image filter regexes ([data_loaders.py:35-40](shared/data_loaders.py#L35-L40)) | Different alt-text patterns will be indexed; `91 image chunks` baseline will shift. |
| Remove the curriculum-first dedup | Multiple chunks from one lesson get separate `[N]` numbers, causing gaps in `lms_references` and broken citations. |

---

## 11. Quick reference — files

| Topic | File |
|---|---|
| GCS download, loaders, chunkers, image extraction | [shared/data_loaders.py](shared/data_loaders.py) |
| Embedding wrapper, vectorstore factory, retriever, context builder, reference extractor | [shared/rag_utils.py](shared/rag_utils.py) |
| Tutor orchestrator, prompt assembly, turn budgeting | [shared/tutor.py](shared/tutor.py) |
| GCP project constants, Secret Manager, DB engine | [shared/config.py](shared/config.py) |
| Build service entrypoint | [build_rag/main.py](build_rag/main.py) |
| Query service entrypoint | [query_rag/main.py](query_rag/main.py) |
| Input/output security gates | [shared/security.py](shared/security.py) |
| Conversation logging | [shared/conversation_store.py](shared/conversation_store.py) |
| File-upload handling (image / .cpp) | [shared/file_handler.py](shared/file_handler.py) |
| Migration runbook + current row counts | [DEPLOYMENT_NOTES.md](DEPLOYMENT_NOTES.md) |