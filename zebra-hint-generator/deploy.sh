#!/usr/bin/env bash
#
# Deploy both Cloud Run services for the Zebra hint generator.
#
#   ./deploy.sh                 # deploy both
#   ./deploy.sh build_rag       # Service A only
#   ./deploy.sh query_rag       # Service B only
#
# Requirements before first run:
#   * gcloud CLI authenticated (`gcloud auth login`) and set to project
#     zebra-ai-assist-poc (`gcloud config set project zebra-ai-assist-poc`).
#   * Secrets GOOGLE_API_KEY, OPENAI_API_KEY, DB_PASSWORD exist in
#     Secret Manager.
#   * Cloud SQL instance zebra-robotics-convo-history exists and has the
#     `vector` extension enabled inside database `conversation_history`.
#   * Runtime service account (see SERVICE_ACCOUNT below) has the roles
#     documented in CLAUDE.md.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID="zebra-ai-assist-poc"
REGION="us-central1"
INSTANCE="zebra-robotics-convo-history"
INSTANCE_CONN="${PROJECT_ID}:${REGION}:${INSTANCE}"
SERVICE_ACCOUNT="773402166266-compute@developer.gserviceaccount.com"

SECRETS="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,DB_PASSWORD=conversation_history_DB-PASSWORD:latest"

# ── Helpers ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }

check_cloud_sql_tier() {
  local tier
  tier=$(gcloud sql instances describe "$INSTANCE" \
           --project="$PROJECT_ID" \
           --format="value(settings.tier)" 2>/dev/null || echo "")
  if [[ -z "$tier" ]]; then
    red "ERROR: Cloud SQL instance '$INSTANCE' not found in project $PROJECT_ID."
    exit 1
  fi
  case "$tier" in
    db-f1-micro|db-g1-small)
      red "ERROR: Cloud SQL tier '$tier' is too small for pgvector at 3072-d."
      red "       Bump to at least db-custom-1-3840 before deploying."
      exit 1
      ;;
    *)
      green "Cloud SQL tier: $tier — OK."
      ;;
  esac
}

copy_shared_into() {
  local svc="$1"
  rm -rf "${svc}/shared"
  cp -R shared "${svc}/shared"
}

cleanup_shared() {
  rm -rf build_rag/shared query_rag/shared
}
trap cleanup_shared EXIT

deploy_build_rag() {
  yellow "── Deploying build-rag-database ──"
  copy_shared_into build_rag
  gcloud run deploy build-rag-database \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --source=build_rag \
    --service-account="$SERVICE_ACCOUNT" \
    --add-cloudsql-instances="$INSTANCE_CONN" \
    --set-secrets="$SECRETS" \
    --no-allow-unauthenticated \
    --memory=4Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=1
  green "build-rag-database deployed."
}

deploy_query_rag() {
  yellow "── Deploying query-rag ──"
  copy_shared_into query_rag
  gcloud run deploy query-rag \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --source=query_rag \
    --service-account="$SERVICE_ACCOUNT" \
    --add-cloudsql-instances="$INSTANCE_CONN" \
    --set-secrets="$SECRETS" \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --timeout=120
  green "query-rag deployed."
}

# ── Run ───────────────────────────────────────────────────────────────────────
target="${1:-both}"

check_cloud_sql_tier

case "$target" in
  build_rag) deploy_build_rag ;;
  query_rag) deploy_query_rag ;;
  both)      deploy_build_rag; deploy_query_rag ;;
  *)
    red "Unknown target '$target'. Use build_rag | query_rag | both."
    exit 1
    ;;
esac

green "Done."
