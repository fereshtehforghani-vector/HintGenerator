#!/usr/bin/env bash
# ============================================================
# deploy.sh — Package and deploy both Cloud Functions to GCP
#
# Usage:
#   ./deploy.sh               # deploy both functions
#   ./deploy.sh build_rag     # deploy only the build function
#   ./deploy.sh query_rag     # deploy only the query function
# ============================================================
set -euo pipefail

PROJECT_ID="zebra-ai-assist-poc"
REGION="us-central1"
RUNTIME="python312"
MEMORY="2Gi"
TIMEOUT="540s"   # 9 min — enough for the full RAG rebuild

gcloud config set project "$PROJECT_ID"

# ── Helper: copy shared/ into a function dir before deploying ────────────────
package_function() {
    local func_dir="$1"
    echo "📦  Packaging $func_dir ..."
    cp -r shared/ "$func_dir/shared"
}

cleanup_function() {
    local func_dir="$1"
    rm -rf "$func_dir/shared"
}

# ── Function A: build_rag_database ───────────────────────────────────────────
deploy_build_rag() {
    echo ""
    echo "🚀  Deploying build-rag-database ..."
    package_function build_rag

    gcloud functions deploy build-rag-database \
        --gen2 \
        --region="$REGION" \
        --runtime="$RUNTIME" \
        --source=build_rag/ \
        --entry-point=build_rag_database \
        --trigger-http \
        --no-allow-unauthenticated \
        --memory="$MEMORY" \
        --timeout="$TIMEOUT" \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID"

    cleanup_function build_rag
    echo "✅  build-rag-database deployed."
}

# ── Function B: query_rag ────────────────────────────────────────────────────
deploy_query_rag() {
    echo ""
    echo "🚀  Deploying query-rag ..."
    package_function query_rag

    gcloud functions deploy query-rag \
        --gen2 \
        --region="$REGION" \
        --runtime="$RUNTIME" \
        --source=query_rag/ \
        --entry-point=query_rag \
        --trigger-http \
        --allow-unauthenticated \
        --memory="1Gi" \
        --timeout="60s" \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID"

    cleanup_function query_rag
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
echo "All done. Function URLs:"
gcloud functions describe build-rag-database --region="$REGION" --gen2 \
    --format="value(serviceConfig.uri)" 2>/dev/null | \
    xargs -I{} echo "  build-rag-database : {}" || true
gcloud functions describe query-rag --region="$REGION" --gen2 \
    --format="value(serviceConfig.uri)" 2>/dev/null | \
    xargs -I{} echo "  query-rag          : {}" || true
