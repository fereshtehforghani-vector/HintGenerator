# GCP Deployment Guide — ZebraBot HintGenerator

## Current stack

| Layer | Choice |
|---|---|
| Embedding model | `gemini-embedding-2-preview` (3072-d) |
| Vector store | Cloud SQL for PostgreSQL 15 + pgvector |
| LLM | GPT-4o (default) or Gemini 2.5 Pro |
| Compute | Cloud Functions Gen 2 |
| Documents | Cloud Storage bucket |
| Secrets | Secret Manager |

---

## GCP resources already set up

### Cloud Storage
- **Bucket:** `zebra-rag-documents`
- **Contents to upload:**
  ```
  LMS/           ← parsed curriculum markdown files
  libraries.pdf  ← Z-Bot C++ library reference
  M1.docx        ← common student mistakes taxonomy
  zebrabot/      ← (optional) ZebraBot firmware source files
  ```

### Cloud SQL
- **Instance:** `zebra-rag-db`  (PostgreSQL 15)
- **Database:** `ragdb`
- **User:** `postgres`
- **Instance connection name:** `zebra-ai-assist-poc:us-central1:zebra-rag-db`

> ⚠️ **Action required — recreate the pgvector table**
>
> The original table was created with `vector(1536)` for OpenAI embeddings.
> The current code uses **Gemini Embedding 2 (3072-d)**, so you must recreate it:
>
> ```sql
> -- Run in Cloud SQL Studio or via psql
> DROP TABLE IF EXISTS langchain_pg_embedding;
> DROP TABLE IF EXISTS langchain_pg_collection;
>
> CREATE EXTENSION IF NOT EXISTS vector;
> ```
>
> LangChain's PGVector will auto-create the tables with the correct 3072-d
> dimension on the first call to `rebuild_vectorstore()`.

### Secret Manager

Add/confirm all three secrets:

| Secret ID | Value |
|---|---|
| `GOOGLE_API_KEY` | Google AI API key (for Gemini Embedding 2 + optionally Gemini LLM) |
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4o) |
| `DB_PASSWORD` | Cloud SQL `postgres` user password |

Create a missing secret:
```bash
echo -n "YOUR_VALUE" | \
  gcloud secrets create GOOGLE_API_KEY \
    --data-file=- \
    --project=zebra-ai-assist-poc
```

### IAM — grant the Cloud Function service account access

```bash
SA="PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Secret Manager
gcloud projects add-iam-policy-binding zebra-ai-assist-poc \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"

# Cloud SQL
gcloud projects add-iam-policy-binding zebra-ai-assist-poc \
  --member="serviceAccount:$SA" \
  --role="roles/cloudsql.client"

# Cloud Storage (for build_rag function)
gcloud projects add-iam-policy-binding zebra-ai-assist-poc \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectViewer"
```

---

## File structure

```
zebra-hint-generator/
├── shared/                  ← Python package imported by both functions
│   ├── __init__.py
│   ├── config.py            ← GCP constants, Secret Manager, Cloud SQL engine
│   ├── data_loaders.py      ← GCS download + document loaders + chunking
│   ├── rag_utils.py         ← GeminiEmbedding2, build_rag_context, vectorstore helpers
│   ├── llm_interface.py     ← LLMInterface (OpenAI / Gemini toggle)
│   ├── tutor.py             ← AgenticTutor, SOCRATIC_SYSTEM_PROMPT, prompt formatters
│   └── security.py          ← input/output guardrails (kid safety)
├── build_rag/
│   ├── main.py              ← Function A: rebuild the RAG database
│   └── requirements.txt
├── query_rag/
│   ├── main.py              ← Function B: answer a student query
│   └── requirements.txt
├── deploy.sh                ← one-command deployment script
└── GCP_DEPLOYMENT.md        ← this file
```

The `deploy.sh` script copies `shared/` into each function directory
before uploading, so Cloud Functions can import it as a local package.

---

## Deploying

```bash
cd zebra-hint-generator

# Deploy both functions
./deploy.sh

# Or individually
./deploy.sh build_rag
./deploy.sh query_rag
```

---

## Function A — `build-rag-database`

**Trigger:** HTTP (authenticated, call manually when documents change)

**What it does:**
1. Fetches secrets from Secret Manager
2. Downloads `LMS/`, `libraries.pdf`, `M1.docx` (and optionally `zebrabot/`) from GCS to `/tmp`
3. Loads + chunks all documents (~350 chunks)
4. Drops and rebuilds the `zbot_chunks` PGVector collection
5. Embeds all chunks with `gemini-embedding-2-preview`
6. Returns `{"status": "success", "chunks_indexed": N}`

**Invoke after deploying:**
```bash
# Get the function URL
URL=$(gcloud functions describe build-rag-database \
        --region=us-central1 --gen2 \
        --format="value(serviceConfig.uri)")

# Trigger with authentication
curl -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{}'

# Dry run (download + chunk, skip embedding)
curl -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

---

## Function B — `query-rag`

**Trigger:** HTTP (publicly accessible — protected by input security guardrails)

**Request:**
```json
{
  "code":      "#include <Arduino.h>\nvoid loop() { ... }",
  "question":  "Why doesn't my sensor ever trigger?",
  "provider":  "OpenAI",
  "course_id": "sdv"
}
```

`course_id` is optional. When provided, LMS chunks are filtered to that course only.
Non-LMS content (library docs, mistake patterns, firmware source) is always searched.

Available course IDs match the LMS subdirectory names with the `rag_output_` prefix removed:

| Directory | `course_id` |
|---|---|
| `rag_output_sdv` | `sdv` |
| `rag_output_reactive_robtics` | `reactive_robtics` |

Omit `course_id` (or set it to `null`) to search the entire LMS.

**Response:**
```json
{
  "response": "🔍 **Mistake Type**: Sensor read not stored...",
  "provider": "OpenAI"
}
```

**Example call:**
```bash
URL=$(gcloud functions describe query-rag \
        --region=us-central1 --gen2 \
        --format="value(serviceConfig.uri)")

curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "#include <Arduino.h>\n#include <ZebraTOF.h>\nZebraTOF tof(2);\nint dist;\nvoid setup(){Wire.begin();tof.begin();}\nvoid loop(){if(dist<100){Serial.println(\"stop\");}}",
    "question": "Why does my stop condition never trigger?"
  }'
```

---

## Local testing with Cloud SQL Auth Proxy

```bash
# 1. Start the proxy
./cloud-sql-proxy zebra-ai-assist-poc:us-central1:zebra-rag-db \
  --port=5432 &

# 2. Set env vars
export GOOGLE_API_KEY="..."
export OPENAI_API_KEY="..."
export DB_PASSWORD="..."

# 3. Run a function locally
cd build_rag
functions-framework --target=build_rag_database --port=8080

# In another terminal:
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

> **Note:** For local testing, the Cloud SQL Auth Proxy binds to `localhost:5432`.
> Override the connection in `config.py` by setting env var `DB_HOST=localhost`
> or by temporarily changing `get_db_engine()` to use a direct psycopg connection string.
