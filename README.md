# Zebra Robotics HintGenerator

A Socratic-style AI tutor for Zebra Robotics students learning C++. It accepts a
student's code and question (or a screenshot / `.cpp` upload), retrieves
relevant lessons from the curriculum via RAG, and returns a hint, a guiding
question, and links back to the source material.

The active codebase is **`zebra-hint-generator/`**. Source material the build
pipeline reads from GCS (parsed LMS markdown, library PDFs, firmware) lives
under `AI Pilot/`.

For deeper detail beyond this README:

- [zebra-hint-generator/RAG_DESIGN.md](zebra-hint-generator/RAG_DESIGN.md) —
  what actually happens inside the RAG pipeline (chunking, embedding,
  retrieval, citation contract).
- [zebra-hint-generator/DEMOS_README.md](zebra-hint-generator/DEMOS_README.md) —
  how to run the `demo_build_rag.sh` and `demo_lms_upload.py` integration
  demos against the deployed services.

---

## Architecture

```
┌────────────────────────┐         ┌────────────────────────┐
│ Frontend (your web app)│  HTTPS  │  Cloud Run: query-rag  │
│                        ├────────►│  (auth-required POST)  │
└────────────────────────┘         └───────────┬────────────┘
                                               │  retrieve top-k
                                               ▼
                                   ┌────────────────────────┐
                                   │  Cloud SQL (pgvector)  │
                                   │  zebra-robotics-       │
                                   │  convo-history         │
                                   │  └─ db: zebra_db       │
                                   │     └─ collection:     │
                                   │        zbot_rag_gcp    │
                                   └───────────▲────────────┘
                                               │  rebuild on demand
                                               │
┌────────────────────────┐  Eventarc  ┌────────┴───────────┐
│ GCS bucket             ├───────────►│ Cloud Run:         │
│ zebra-rag-documents    │  finalize  │ build-rag-database │
│ └─ LMS/LMS_PARSED/...  │  events    │ (auth-required)    │
│ └─ libraries.pdf       │            └────────────────────┘
└────────────────────────┘
```

Two Cloud Run services share a `shared/` Python package:

- **`query-rag`** — Public-facing tutoring endpoint. Loads a student's code/question,
  retrieves the top-k curriculum chunks from pgvector, runs the LLM, and
  streams the response back. Citations link to the original lesson markdown
  in GCS.
- **`build-rag-database`** — Re-embeds the knowledge base from scratch. Triggered
  automatically when files change in `gs://zebra-rag-documents/LMS/LMS_PARSED/`,
  or manually via curl. Drops and recreates the `zbot_rag_gcp` collection.

The collection holds 416 vector chunks today (325 text + 91 image) at 3072
dimensions (Gemini Embedding 2).

---

## Repo layout

```
zebra-hint-generator/
├── build_rag/                 # Cloud Run service A: knowledge-base builder
│   ├── main.py                # Flask app — POST / triggers a rebuild
│   ├── Dockerfile
│   └── requirements.txt
├── query_rag/                 # Cloud Run service B: tutoring endpoint
│   ├── main.py                # Flask app — POST / streams a hint back
│   ├── Dockerfile
│   └── requirements.txt
├── shared/                    # Imported by both services. deploy.sh copies
│   ├── config.py              #   it into each service dir at deploy time.
│   ├── conversation_store.py
│   ├── data_loaders.py        # GCS download + chunking
│   ├── file_handler.py        # Image / .cpp upload handling
│   ├── llm_interface.py       # OpenAI / Gemini wrapper
│   ├── rag_utils.py           # Embedding + pgvector helpers
│   ├── security.py            # Input/output guardrails
│   └── tutor.py               # AgenticTutor — orchestrates retrieve + LLM
├── deploy.sh                  # Deploy build_rag and/or query_rag to Cloud Run
├── RAG_DESIGN.md              # Design doc — what the RAG pipeline does internally
├── DEMOS_README.md            # How to run the build_rag integration demos
├── demo_build_rag.sh          # Demo — POST the deployed build-rag-database end-to-end
├── demo_lms_upload.py         # Demo — verify Eventarc auto-rebuild on LMS upload
├── demo_show_db.py            # Demo helper — print pgvector collection stats
├── test_frontend.py           # Developer tool — Gradio chat UI for the deployed query-rag
└── test_frontend.sh           # Convenience wrapper — `cd`s into the service dir and runs `python test_frontend.py`
```

`AI Pilot/` (sibling of `zebra-hint-generator/`) holds source material the
build pipeline reads from GCS — markdown lessons under
`Vector_AI/LMS/LMS_PARSED/`, `libraries.pdf`, firmware source.

The files at the bottom of the tree (`demo_*`, `test_frontend*`) are
**developer-only utilities** for integration testing and demos. They are
**not** what gets deployed — they're helpers you run from your laptop. The
production pipeline is `build_rag/` and `query_rag/`.

---

## Prerequisites

- **gcloud CLI** authenticated against project `zebra-ai-assist-poc`:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  gcloud config set project zebra-ai-assist-poc
  ```
- **Python 3.12+** (the deployed services use 3.12; local works on 3.13).
- A virtualenv with the dependencies from the repo-root `requirements.txt`
  (a slimmed-down superset that covers both services and the dev tools):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
  Each service also ships its own pinned `requirements.txt`
  (`zebra-hint-generator/build_rag/requirements.txt`,
  `zebra-hint-generator/query_rag/requirements.txt`) — those are what Cloud
  Run actually builds against.

---

## Cloud infrastructure (already provisioned)

| Resource | Name |
|---|---|
| Project | `zebra-ai-assist-poc` |
| Region | `us-central1` |
| Cloud SQL instance | `zebra-robotics-convo-history` (Postgres 18, db-custom-2-8192) |
| Database | `zebra_db` |
| pgvector collection | `zbot_rag_gcp` |
| GCS bucket (sources) | `zebra-rag-documents` |
| GCS bucket (uploads) | `zebra-robotics-images` |
| Cloud Run service A | `build-rag-database` |
| Cloud Run service B | `query-rag` |
| Secrets in Secret Manager | `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `conversation_history_DB-PASSWORD`, `conversation_history_DB-USER`, `conversation_history_DB_NAME` |

The runtime service account for both Cloud Run services is the project's
**default compute SA** (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`).
It already has `cloudsql.client`, `secretmanager.secretAccessor`,
`storage.objectAdmin`, and `artifactregistry.writer`.

---

## Deploying to GCP

From `zebra-hint-generator/`:

```bash
./deploy.sh                 # both services
./deploy.sh build_rag       # service A only
./deploy.sh query_rag       # service B only
```

Each deploy takes 5–8 minutes (most of it Cloud Build compiling the Python
container). The script:

1. Verifies the Cloud SQL tier is large enough for 3072-d pgvector.
2. Copies `shared/` into the service directory (Cloud Run's source builder
   only sees files inside the deployed dir).
3. Runs `gcloud run deploy --source <service>/`.
4. Cleans up the copied `shared/` on exit.

After deploy, `query-rag` needs a public-invoker IAM binding so the frontend
can call it without authentication:

```bash
gcloud run services add-iam-policy-binding query-rag \
  --region=us-central1 --project=zebra-ai-assist-poc \
  --member=allUsers --role=roles/run.invoker
```

`build-rag-database` stays auth-required (only Eventarc / authenticated
operators should be able to trigger a rebuild).

---

## Auto-rebuild on LMS bucket changes (Eventarc)

`build-rag-database` is wired to fire whenever a file is finalized in
`gs://zebra-rag-documents/`. The service has an in-process guard that
short-circuits rebuilds for objects outside `LMS/LMS_PARSED/` — so changes
to `libraries.pdf` or other paths don't trigger a $0.50 re-embed.

### One-time IAM bindings

```bash
PROJECT=zebra-ai-assist-poc
PROJECT_NUMBER=773402166266

# 1. GCS service agent can publish to Pub/Sub (for direct storage events)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

# 2. Eventarc service agent can mint tokens to invoke Cloud Run
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

# 3. The trigger SA can invoke the auth-only Cloud Run service
gcloud run services add-iam-policy-binding build-rag-database \
  --region=us-central1 --project=$PROJECT \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Create the trigger

The currently wired trigger is `build-rag-on-bucket-change` (referenced by
`demo_lms_upload.py`). To recreate it from scratch:

```bash
gcloud eventarc triggers create build-rag-on-bucket-change \
  --location=us-central1 \
  --destination-run-service=build-rag-database \
  --destination-run-region=us-central1 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=zebra-rag-documents" \
  --service-account=773402166266-compute@developer.gserviceaccount.com \
  --project=zebra-ai-assist-poc
```

A rebuild takes ~6–8 minutes and costs ~$0.50 in Gemini API calls. With
`max-instances=1`, concurrent triggers queue rather than run in parallel.

---

## Manual operations

### Trigger a rebuild manually

```bash
URL=$(gcloud run services describe build-rag-database \
        --region=us-central1 --project=zebra-ai-assist-poc \
        --format="value(status.url)")
curl -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{}'

# Dry-run (download + chunk only, no embedding):
curl -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

### Smoke-test query-rag

```bash
URL=$(gcloud run services describe query-rag \
        --region=us-central1 --project=zebra-ai-assist-poc \
        --format="value(status.url)")
curl -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "int x=0; void loop(){Serial.println(x);}",
    "question": "Why does x never change?",
    "provider": "OpenAI",
    "course_id": "sdv"
  }'
```

The response streams as `text/plain`. Curriculum references come back in the
`X-LMS-References` response header (JSON-encoded array). The conversation id
is in `X-Conversation-ID`.

---

## Developer tools (not deployed)

These run from your laptop and are useful for exercising the deployed
services end-to-end before/after a change. There is no unit-test framework
in this repo — these scripts are hand-run integration demos.

### `test_frontend.py` — Gradio chat UI against the deployed query-rag

A local web app (Gradio) that lets you chat with the deployed `query-rag`
service end-to-end, including the C++ code box for cpp-track students. It
pulls a fresh identity token from gcloud on every request, so make sure
you're logged in (`gcloud auth login`). The gcloud lookup uses
`shutil.which("gcloud")`, so it works on macOS, Linux, and Windows
(`gcloud.cmd`) without modification.

To run it, set the deployed URL in your environment and launch:

```python
cd zebra-hint-generator
python test_frontend.py
# opens http://127.0.0.1:7860
```

Or, in test_frontend.py, comment out the hardcoded URL and uncomment the os.environ line (QUERY_RAG_URL = "[URL link]", QUERY_RAG_URL = os.environ.get("QUERY_RAG_URL")) , then run:

```bash
cd zebra-hint-generator
export QUERY_RAG_URL=$(gcloud run services describe query-rag \
        --region=us-central1 --project=zebra-ai-assist-poc \
        --format="value(status.url)")
python test_frontend.py
# opens http://127.0.0.1:7860
```

Or just use the wrapper, which `cd`s into the service directory and runs
`python test_frontend.py`:

```bash
cd zebra-hint-generator
./test_frontend.sh
```

### `demo_build_rag.sh` — integration demo for `build-rag-database`

Hits the deployed `build-rag-database` Cloud Run service end-to-end,
verifies the pgvector collection state via `demo_show_db.py`, and
optionally proves the Eventarc path-filter guard by uploading a file
*outside* `LMS/LMS_PARSED/`. Supports `--dry-run` (no embedding spend) and
`--with-eventarc`.

```bash
cd zebra-hint-generator
./demo_build_rag.sh --dry-run                   # safe, no DB writes
./demo_build_rag.sh                             # real rebuild — spends embedding quota
./demo_build_rag.sh --dry-run --with-eventarc   # also tests path-filter guard
```

### `demo_lms_upload.py` — verify the Eventarc auto-rebuild path

Uploads a copy of an existing SDV lesson to
`gs://zebra-rag-documents/LMS/LMS_PARSED/rag_output_sdv/...`, watches the
Eventarc-triggered rebuild land in pgvector, and cleans up afterwards.

```bash
cd zebra-hint-generator
python3 demo_lms_upload.py                       # default source + cleanup
python3 demo_lms_upload.py --keep                # leave the demo file in GCS
python3 demo_lms_upload.py --source 05_working_with_motors.md \
                           --name   99_demo_motors_copy.md
```

### `demo_show_db.py` — print pgvector collection stats

Stand-alone helper used by `demo_build_rag.sh` and runnable on its own to
print collection name, total chunk count, breakdown by `type` and
`course_id`, and the embedding dimension of a real row.

```bash
cd zebra-hint-generator
python3 demo_show_db.py
```

See [zebra-hint-generator/DEMOS_README.md](zebra-hint-generator/DEMOS_README.md)
for prerequisites, expected output, and failure-mode troubleshooting.

---

## Inspecting and debugging

### Cloud Run logs

```bash
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name=query-rag' \
  --project=zebra-ai-assist-poc --limit=50 --order=desc \
  --format="value(timestamp,severity,textPayload,httpRequest.status)"
```

Or in the console: `Cloud Run → <service> → Logs`. The "Stream logs" button
gives you live tailing without installing extra gcloud components.

### Inspect the pgvector collection

```bash
gcloud sql connect zebra-robotics-convo-history \
  --user=zebra_db_user --database=zebra_db
# at psql:
SELECT name FROM langchain_pg_collection;
SELECT cmetadata->>'type', count(*)
  FROM langchain_pg_embedding e
  JOIN langchain_pg_collection c ON e.collection_id=c.uuid
  WHERE c.name='zbot_rag_gcp'
  GROUP BY 1;
```

---

## Editing & gotchas

- **Reordering retrieval docs** in `build_rag_context`, or skipping the
  curriculum-first dedup, will silently desync `lms_references[].ref` from
  the `[N]` citations the LLM produces.
- **Embedding dimension is 3072** (Gemini Embedding 2). If you ever switch
  embedding models, drop `langchain_pg_embedding` and `langchain_pg_collection`
  first — LangChain's PGVector recreates them with the new dimension on the
  next `rebuild_vectorstore()`.
- **`shared/` gets copied into each service dir at deploy time** by `deploy.sh`
  and cleaned up on exit. Don't commit `build_rag/shared/` or `query_rag/shared/` —
  those are transient.
- **Course filter slugs** are derived from LMS folder names with the
  `rag_output_` prefix stripped: today they are `sdv` and `reactive_robtics`
  (the typo is the directory name on disk — keep it). Pass `course_id` in the
  request body to scope retrieval to one course.

---

## Useful console links

- [Cloud Run services](https://console.cloud.google.com/run?project=zebra-ai-assist-poc)
- [Cloud SQL instance](https://console.cloud.google.com/sql/instances/zebra-robotics-convo-history/overview?project=zebra-ai-assist-poc)
- [GCS source bucket](https://console.cloud.google.com/storage/browser/zebra-rag-documents?project=zebra-ai-assist-poc)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=zebra-ai-assist-poc)
- [Eventarc triggers](https://console.cloud.google.com/eventarc/triggers?project=zebra-ai-assist-poc)
- [Cloud Build history](https://console.cloud.google.com/cloud-build/builds?project=zebra-ai-assist-poc)
