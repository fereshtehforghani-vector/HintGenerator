#!/usr/bin/env bash
#
# demo_build_rag.sh — narrate the deployed build_rag service to an audience.
#
# DEFAULT BEHAVIOR: triggers a REAL rebuild of the pgvector collection in
# zebra_db (instance: zebra-robotics-convo-history). This overwrites the
# existing langchain_pg_embedding rows for the active collection and costs
# Gemini embedding quota.
#
# Usage:
#   ./demo_build_rag.sh                   # real rebuild (writes to Cloud SQL)
#   ./demo_build_rag.sh --dry-run         # safe mode: chunk-only, no DB writes
#   ./demo_build_rag.sh --with-eventarc   # also demo the bucket-trigger guard
#
# Flow:
#   Step 0 → tell user to tail logs in a 2nd terminal
#   Step 1 → resolve the deployed Cloud Run service URL
#   Step 2 → BEFORE: read-only inspection of the current pgvector contents
#   Step 3 → POST to the service (real rebuild OR dry_run, per --dry-run flag)
#   Step 4 → AFTER:  re-inspect to confirm the row count changed (real rebuild)
#   Step 5 → (--with-eventarc) demo the LMS/LMS_PARSED/ path-filter guard
#
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="zebra-ai-assist-poc"
REGION="us-central1"
SERVICE="build-rag-database"
BUCKET="zebra-rag-documents"
SAFE_OBJECT="demo/non-lms-trigger.txt"   # NOT under LMS/LMS_PARSED/

# ── Output helpers ────────────────────────────────────────────────────────────
cyan()   { printf "\033[1;36m%s\033[0m\n" "$*"; }
yellow() { printf "\033[1;33m%s\033[0m\n" "$*"; }
green()  { printf "\033[1;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[1;31m%s\033[0m\n" "$*"; }
step()   { echo; cyan "── $* ──"; }
pause()  { read -r -p "  press <enter> to continue..." _; }

# ── Args ──────────────────────────────────────────────────────────────────────
WITH_EVENTARC=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --with-eventarc) WITH_EVENTARC=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) red "unknown arg: $arg"; exit 1 ;;
  esac
done

# ── Preflight ─────────────────────────────────────────────────────────────────
for cmd in gcloud gsutil curl; do
  command -v "$cmd" >/dev/null 2>&1 || { red "$cmd not found in PATH"; exit 1; }
done

ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
if [[ "$ACTIVE_PROJECT" != "$PROJECT_ID" ]]; then
  red "  Active gcloud project is '$ACTIVE_PROJECT' but this demo expects '$PROJECT_ID'."
  red "  Run:  gcloud config set project $PROJECT_ID"
  exit 1
fi

# Always use the project's .venv python so the user doesn't have to activate it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/bin/python3"
if [[ ! -x "$VENV_PY" ]]; then
  red "  $VENV_PY not found. Create it once with:"
  red "    cd $SCRIPT_DIR && python3 -m venv .venv && source .venv/bin/activate \\"
  red "      && pip install sqlalchemy pg8000 'cloud-sql-python-connector[pg8000]' \\"
  red "                     google-cloud-secret-manager google-cloud-storage"
  exit 1
fi

# ── Step 0 · log tail in a second terminal ────────────────────────────────────
step "Step 0 · Open Cloud Run logs in a SECOND terminal"
echo "  Run this in another window so the audience can watch logs live:"
echo
yellow "  gcloud run services logs tail $SERVICE --region=$REGION --project=$PROJECT_ID"
echo
echo "  (If your gcloud is older: gcloud beta run services logs tail ...)"
pause

# ── Step 1 · service URL ──────────────────────────────────────────────────────
step "Step 1 · Resolve the deployed service URL"
URL=$(gcloud run services describe "$SERVICE" \
        --region="$REGION" --project="$PROJECT_ID" \
        --format='value(status.url)')
green "  $URL"
pause

# ── Step 2 · Inspect what build_rag wrote to Cloud SQL ────────────────────────
step "Step 2 · What's currently in pgvector (read-only SELECTs)"
cat <<EOF
  We connect to the Cloud SQL instance with the SAME code path the deployed
  build_rag uses (Cloud SQL Python Connector + pg8000, see shared/config.py)
  and run a few SELECTs to show:

    • the pgvector collection registered by build_rag
    • the langchain_pg_embedding table schema (incl. vector(3072) column)
    • the actual embedding dimension on a real row
    • total chunks, chunks-by-type, curriculum-by-course breakdowns
    • a few sample rows so the audience sees real metadata

  Only SELECTs run — no writes.
EOF
echo
if "$VENV_PY" "$SCRIPT_DIR/demo_show_db.py"; then
  green "  DB inspection complete."
else
  yellow "  DB inspection failed (likely missing IAM, Python deps, or DB_PASSWORD)."
  yellow "  Continuing — this step is informational; the DB is unaffected either way."
fi
pause

# ── Step 3 · Trigger rebuild (or dry_run) ─────────────────────────────────────
if [[ $DRY_RUN -eq 1 ]]; then
  step "Step 3 · dry_run health-check (NO writes to Cloud SQL)"
  POST_BODY='{"dry_run": true}'
  CURL_TIMEOUT=180
  cat <<EOF
  --dry-run mode: POST {"dry_run": true} to the service. The handler hydrates
  secrets, downloads + chunks docs from gs://$BUCKET/, then EXITS before any
  DB write. Use this when you want to demo build_rag without rebuilding.
EOF
else
  step "Step 3 · REAL REBUILD — overwrite the pgvector collection"
  POST_BODY='{}'
  CURL_TIMEOUT=1800
  cat <<EOF
  POST {} to the service. The handler:
    • Hydrates secrets (GOOGLE_API_KEY, OPENAI_API_KEY, DB_PASSWORD).
    • Downloads every doc from gs://$BUCKET/.
    • Chunks them, then EMBEDS each chunk with Gemini Embedding 2 (3072-d).
    • Drops + recreates the rows for the active collection in
      langchain_pg_embedding (instance: zebra-robotics-convo-history,
      database: zebra_db).
    • Returns {status: success, chunks_indexed: N}.
EOF
  echo
  red "  This OVERWRITES rows in Cloud SQL and costs Gemini embedding quota."
  red "  Expected runtime: ~1-3 min for ~400 chunks."
fi
echo
yellow "  curl -X POST \$URL -d '$POST_BODY'  (timeout ${CURL_TIMEOUT}s)"
RESPONSE=$(curl -sS --max-time "$CURL_TIMEOUT" -X POST "$URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d "$POST_BODY")
echo
green "  Response: $RESPONSE"

# ── Step 4 · AFTER inspection (only on a real rebuild) ────────────────────────
if [[ $DRY_RUN -eq 0 ]]; then
  pause
  step "Step 4 · DB AFTER — confirm the rebuild landed"
  echo "  Re-running the read-only inspector. Compare 'Total chunks indexed'"
  echo "  against the BEFORE snapshot in Step 2 — it should match the"
  echo "  chunks_indexed count returned by Step 3."
  echo
  if "$VENV_PY" "$SCRIPT_DIR/demo_show_db.py"; then
    green "  AFTER inspection complete."
  else
    yellow "  AFTER inspection failed (informational only — rebuild already returned success above)."
  fi
fi

# ── Step 5 · (optional) Eventarc path-filter demo ─────────────────────────────
if [[ $WITH_EVENTARC -eq 1 ]]; then
  pause
  step "Step 5 · Eventarc trigger guard — non-LMS upload"
  cat <<EOF
  We upload a junk file at:
      gs://$BUCKET/$SAFE_OBJECT
  This path is OUTSIDE LMS/LMS_PARSED/, so build_rag's filter
  (build_rag/main.py:48-56) returns 'skipped' before any DB code runs.

  This proves:
    • The Eventarc storage trigger is wired to the bucket.
    • The path-filter guard protects pgvector from accidental rebuilds
      whenever someone touches an unrelated bucket object.
EOF
  pause

  TMPFILE=$(mktemp)
  echo "demo payload — see demo_build_rag.sh, safe to delete" > "$TMPFILE"
  cleanup() {
    rm -f "$TMPFILE" 2>/dev/null || true
    gsutil -q rm "gs://$BUCKET/$SAFE_OBJECT" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  yellow "  uploading gs://$BUCKET/$SAFE_OBJECT ..."
  gsutil -q cp "$TMPFILE" "gs://$BUCKET/$SAFE_OBJECT"
  green "  uploaded."
  echo
  echo "  Watch your log-tail terminal. Within ~5-15s you should see:"
  yellow "    Skipping: event for $BUCKET/$SAFE_OBJECT is outside LMS/LMS_PARSED/"
  echo
  echo "  If nothing appears in the logs after ~30s, the Eventarc trigger"
  echo "  isn't wired to this bucket — but the DB is still safe (this demo"
  echo "  never calls rebuild_vectorstore)."
  pause

  yellow "  cleaning up gs://$BUCKET/$SAFE_OBJECT ..."
  cleanup
  trap - EXIT INT TERM
  green "  cleaned up."
fi

# ── Recap ─────────────────────────────────────────────────────────────────────
step "Done · what we just showed"
echo "  • build_rag is deployed and reachable at:"
echo "      $URL"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  • --dry-run mode: pipeline ran end-to-end up to (but not including)"
  echo "    the embedding + DB write. Cloud SQL was NOT modified."
else
  echo "  • REAL REBUILD: the pgvector collection in zebra_db has been"
  echo "    overwritten. test_frontend.py will now query the freshly"
  echo "    indexed chunks — citations point at the latest LMS docs."
fi
if [[ $WITH_EVENTARC -eq 1 ]]; then
  echo "  • The bucket trigger fires on changes, and the path filter protects"
  echo "    Cloud SQL from non-LMS noise."
fi
green "demo complete."
