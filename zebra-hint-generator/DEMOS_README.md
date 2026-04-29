# build_rag demo scripts

Two hand-run integration demos for the deployed `build-rag-database` Cloud Run
service. They are **not unit tests** — they exercise the real production
pipeline against real Cloud SQL (`zebra-rag-db`) and burn real Gemini
embedding quota.

| Script | What it proves |
| --- | --- |
| [demo_build_rag.sh](demo_build_rag.sh) | The deployed service is reachable, secrets hydrate, the GCS → chunk → embed → pgvector pipeline runs end-to-end, and the Eventarc path-filter guard rejects non-LMS uploads. |
| [demo_lms_upload.py](demo_lms_upload.py) | Uploading a new file to `gs://zebra-rag-documents/LMS/LMS_PARSED/...` auto-triggers a rebuild via Eventarc, and the new file actually lands as embedded chunks in pgvector. |

---

## Prerequisites (both scripts)

1. **Active gcloud project** must be `zebra-ai-assist-poc`:
   ```bash
   gcloud config set project zebra-ai-assist-poc
   gcloud auth login
   gcloud auth application-default login
   ```
2. **`build-rag-database` is deployed** in `us-central1`. If not:
   ```bash
   cd zebra-hint-generator && ./deploy.sh build_rag
   ```
3. **Project virtualenv** at `zebra-hint-generator/.venv` with deps:
   ```bash
   cd zebra-hint-generator
   python3 -m venv .venv && source .venv/bin/activate
   pip install sqlalchemy pg8000 'cloud-sql-python-connector[pg8000]' \
               google-cloud-secret-manager google-cloud-storage
   ```
4. **DB password** available either via `DB_PASSWORD` env var or via Secret
   Manager (`conversation_history_DB-PASSWORD`) — your account needs
   `roles/secretmanager.secretAccessor`.
5. CLI tools on PATH: `gcloud`, `gsutil`, `curl`.

---

## demo_build_rag.sh

### What it tests

| Step | What's verified |
| --- | --- |
| Preflight | `gcloud`/`gsutil`/`curl` installed; active project matches; `.venv` Python exists. |
| 1. Service URL | `build-rag-database` is deployed in `us-central1` and Cloud Run returns a URL. |
| 2. DB inspection (read-only) | Cloud SQL Connector + pg8000 auth works; the `langchain_pg_collection` row exists; `langchain_pg_embedding` has a `vector(3072)` column; a real row's embedding is 3072-d; chunk counts by `type` and by `course_id` are sane. |
| 3. POST to service | Secret hydration → GCS download → chunking → (in real mode) Gemini Embedding 2 → drop+recreate pgvector rows. Returns `{status, chunks_indexed}`. |
| 4. (`--with-eventarc`) Path-filter guard | Uploading a file *outside* `LMS/LMS_PARSED/` causes the service to log `Skipping: ...` and exit before any DB code runs — proves the trigger is wired AND properly gated. |

### How to run

```bash
cd zebra-hint-generator

# Safe mode — chunks docs but does NOT embed or write to Cloud SQL.
./demo_build_rag.sh --dry-run

# Real rebuild — overwrites pgvector and burns embedding quota (~1–3 min).
./demo_build_rag.sh

# Add the optional Eventarc path-filter demo at the end.
./demo_build_rag.sh --with-eventarc
./demo_build_rag.sh --dry-run --with-eventarc
```

In a **second terminal**, tail logs so you (and the audience) can see the
service work in real time:
```bash
gcloud run services logs tail build-rag-database \
  --region=us-central1 --project=zebra-ai-assist-poc
```

### Expected output (healthy run)

- **Step 1**: a green Cloud Run URL like
  `https://build-rag-database-xxxxx-uc.a.run.app`.
- **Step 2**: a printed table from `demo_show_db.py` showing the collection,
  total chunk count, breakdown by `type` (`curriculum`, `library`,
  `firmware`, `mistake`), curriculum chunks per `course_id` (`sdv`,
  `reactive_robtics`), and a confirmed embedding dimension of `3072`. Ends
  with `DB inspection complete.` in green.
- **Step 3 (`--dry-run`)**: response body
  `{"status":"dry_run","chunks":N,...}` — no DB rows changed.
- **Step 3 (real)**: response body
  `{"status":"success","chunks_indexed":N}` (typically a few hundred). Logs
  in the second terminal show download → chunk → batch embedding progress.
- **Step 4 (`--with-eventarc`)**: log tail shows
  `Skipping: event for zebra-rag-documents/demo/non-lms-trigger.txt is outside LMS/LMS_PARSED/`
  within 5–15s of the upload. The script then deletes the temp object and
  prints `cleaned up.`
- **Recap**: `demo complete.` in green.

### Failure signals

- Step 2 prints `DB inspection failed (likely missing IAM, Python deps, or DB_PASSWORD).` — informational only; the demo continues.
- Step 3 returns non-2xx, or the response is missing `chunks_indexed` → check the log tail for stack traces in `build-rag-database`.
- Step 4 log line never appears within ~30s → the Eventarc trigger isn't wired to this bucket (DB still safe — this step never calls `rebuild_vectorstore`).

---

## demo_lms_upload.py

### What it tests

End-to-end **auto-rebuild via Eventarc**:
1. Snapshots `(collection_uuid, total_chunks, sdv_chunks)` from
   `langchain_pg_collection` / `langchain_pg_embedding`.
2. Drains the Pub/Sub subscription backing the Eventarc trigger so stale
   redeliveries don't fire spurious rebuilds during the demo.
3. Describes the wired Eventarc trigger (`build-rag-on-bucket-change`) so
   the audience sees the bucket → service link.
4. Uploads a copy of an existing SDV lesson under a new filename to
   `gs://zebra-rag-documents/LMS/LMS_PARSED/rag_output_sdv/<new>.md`.
5. Polls pgvector every 10s and asserts:
   - the **collection uuid changes** (drop + create ran), and
   - the **chunk count climbs back to ≥ the BEFORE total** (guards against
     the text/image plateau where text commits first, then images), and
   - **chunks tagged with the new filename exist** (`cmetadata->>'source' LIKE '%<name>%'`).
6. Cleanup (default): deletes the GCS blob, manually POSTs to the service
   (GCS `deleted` events don't fire the trigger — only `finalized` does),
   and waits for the cleanup rebuild to stabilize.

### How to run

```bash
cd zebra-hint-generator

# Default: copies 00_course_overview.md as 99_demo_new_lesson.md, then cleans up.
python3 demo_lms_upload.py

# Use a different SDV lesson as the source, and pick the demo filename.
python3 demo_lms_upload.py --source 05_working_with_motors.md \
                           --name   99_demo_motors_copy.md

# Leave the demo file in GCS (skip cleanup rebuild).
python3 demo_lms_upload.py --keep

# Bigger per-rebuild timeout (default 600s).
python3 demo_lms_upload.py --timeout 900
```

Optional log tail in a second terminal:
```bash
gcloud run services logs tail build-rag-database \
  --region=us-central1 --project=zebra-ai-assist-poc
```

### Expected output (healthy run)

```
Connecting to Cloud SQL via Cloud SQL Python Connector...

── Step 0 · Drain Pub/Sub backlog ──
  drained Pub/Sub subscription up to 2026-04-29T...Z

── Step 1 · BEFORE — wait for a stable starting state, then snapshot ──
  t+  0s  uuid=abcd1234  total=415  sdv=214
  t+ 10s  uuid=abcd1234  total=415  sdv=214
  t+ 20s  uuid=abcd1234  total=415  sdv=214
  collection uuid : abcd1234-...
  total chunks    : 415
  sdv chunks      : 214
  chunks already pointing at '99_demo_new_lesson.md': 0

── Step 2 · Eventarc trigger 'build-rag-on-bucket-change' ──
  projects/.../triggers/build-rag-on-bucket-change  build-rag-database  [bucket=zebra-rag-documents,...]

── Step 3 · Upload 00_course_overview.md → gs://zebra-rag-documents/LMS/LMS_PARSED/rag_output_sdv/99_demo_new_lesson.md ──
  uploaded gs://zebra-rag-documents/...  (1234 bytes)
  upload complete — Eventarc should fire build-rag-database now.

── Step 4 · Watch the auto-triggered rebuild ──
  t+ 10s  uuid=same  total=415  sdv=214
  t+ 30s  uuid=NEW   total=0    sdv=0      ← drop+create
  t+ 70s  uuid=NEW   total=120  sdv=60     ← text batches landing
  t+130s  uuid=NEW   total=327  sdv=170    ← text plateau
  t+200s  uuid=NEW   total=417  sdv=216    ← images committed
  ...stable for 3 polls...

── Step 5 · AFTER — confirm the new file was indexed ──
  collection uuid : <new-uuid>     (new — drop+create ran)
  total chunks    : 415  →  417     (+2)
  sdv chunks      : 214  →  216     (+2)
  chunks for '99_demo_new_lesson.md': 0  →  2     ✓ new doc was chunked + embedded + saved
  rebuild wall time: ~210s

── Step 6 · Cleanup ──
  Deleting demo file from GCS...
  deleted gs://zebra-rag-documents/.../99_demo_new_lesson.md
  Triggering rebuild via authenticated POST...
  manual trigger accepted; rebuild started.
  Waiting for cleanup rebuild to finish ...
  cleanup rebuild done: total=415  sdv=214

✓ demo complete.
```

The exact chunk numbers vary every run — they depend on (a) the current
contents of `gs://zebra-rag-documents/` and (b) the size of the file you
upload. The default `--source 00_course_overview.md` is a short overview
page that produces only ~2 chunks; a longer lesson like
`05_working_with_motors.md` will produce many more. What matters for a
healthy run is the **shape**, not the absolute numbers:

- `uuid=NEW` appears in Step 4 (drop+create ran).
- The three deltas in Step 5 are **internally consistent**: `total chunks`
  delta == `sdv chunks` delta == `chunks for '<name>'` (when the source is
  an SDV file). All three should equal the chunk count of the uploaded file.
- `chunks for '<name>'` is **> 0** with the green `✓` line.
- Cleanup rebuild restores roughly the BEFORE total.

### Failure signals

- `collection 'rag_chunks' does not exist yet` → never built. Run
  `demo_build_rag.sh` (real mode) once first.
- Step 4 hangs and eventually `TimeoutError: Rebuild did not finish+stabilize within ...s` → the Eventarc trigger didn't fire, or the service is failing. Check the log tail; verify the trigger exists with `gcloud eventarc triggers describe build-rag-on-bucket-change --location=us-central1`.
- `chunks for '<name>': 0 → 0` with red `✗ demo file produced 0 chunks` → a rebuild did happen but the new file wasn't picked up; check the path filter in `build_rag/main.py` and that `--name` is under `rag_output_sdv/`.
- `(could not seek subscription: ...)` or `(could not describe trigger: ...)` are non-fatal — your account just lacks the read role for that resource; the demo continues.

---

## Cost / safety notes

- Real-mode runs **overwrite** rows in `langchain_pg_embedding` for the
  active collection. There is no rollback — re-running the build (or the
  cleanup step in `demo_lms_upload.py`) is the recovery path.
- Each full rebuild costs Gemini Embedding 2 quota for ~400 chunks at 3072-d.
- Use `demo_build_rag.sh --dry-run` for any demo where you don't actually
  need fresh embeddings — it stops before the embed/write phase.
