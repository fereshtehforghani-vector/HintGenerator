#!/usr/bin/env bash
# ============================================================
# deploy.sh — Build and deploy both Cloud Run services to GCP
#
# Usage:
#   ./deploy.sh               # deploy both services
#   ./deploy.sh build_rag     # deploy only the build service
#   ./deploy.sh query_rag     # deploy only the query service
# ============================================================
set -euo pipefail

PROJECT_ID="zebra-ai-assist-poc"
REGION="us-central1"
MEMORY_BUILD="2Gi"
MEMORY_QUERY="1Gi"
TIMEOUT_BUILD="3600"   # 1 hour — enough for a full RAG rebuild
TIMEOUT_QUERY="60"

gcloud config set project "$PROJECT_ID"

# ── Helper: copy shared/ into a service dir before building ─────────────────
package_service() {
    local svc_dir="$1"
    echo "📦  Packaging $svc_dir ..."
    cp -r shared/ "$svc_dir/shared"
}

cleanup_service() {
    local svc_dir="$1"
    rm -rf "$svc_dir/shared"
}

# ── Service A: build-rag-database ────────────────────────────────────────────
deploy_build_rag() {
    echo ""
    echo "🚀  Deploying build-rag-database ..."
    package_service build_rag

    gcloud run deploy build-rag-database \
        --source=build_rag/ \
        --region="$REGION" \
        --no-allow-unauthenticated \
        --memory="$MEMORY_BUILD" \
        --timeout="$TIMEOUT_BUILD" \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID"

    cleanup_service build_rag
    echo "✅  build-rag-database deployed."
}

# ── Service B: query-rag ─────────────────────────────────────────────────────
deploy_query_rag() {
    echo ""
    echo "🚀  Deploying query-rag ..."
    package_service query_rag

    gcloud run deploy query-rag \
        --source=query_rag/ \
        --region="$REGION" \
        --allow-unauthenticated \
        --memory="$MEMORY_QUERY" \
        --timeout="$TIMEOUT_QUERY" \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID"

    cleanup_service query_rag
    echo "✅  query-rag deployed."
}

# ── Main ─────────────────────────────────────────────────────────────────────
TARGET="${1:-both}"

case "$TARGET" in
    build_rag) deploy_build_rag ;;
    query_rag) deploy_query_rag ;;
    both)
        deploy_build_rag
        deploy_query_rag
        ;;
    *)
        echo "Unknown target: $TARGET  (use build_rag | query_rag | both)"
        exit 1
        ;;
esac

echo ""
echo "Service URLs:"
gcloud run services describe build-rag-database --region="$REGION" \
    --format="value(status.url)" 2>/dev/null | \
    xargs -I{} echo "  build-rag-database : {}" || true
gcloud run services describe query-rag --region="$REGION" \
    --format="value(status.url)" 2>/dev/null | \
    xargs -I{} echo "  query-rag          : {}" || true
