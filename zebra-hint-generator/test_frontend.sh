#!/usr/bin/env bash
#
# Local launcher for test_frontend.py.
#
# Keeps the deployed Cloud Run URL out of the source file so test_frontend.py
# is safe to push publicly. This script is intended to stay local — gitignore
# it (or commit a sanitized .example version with QUERY_RAG_URL=...).
#
# Requires:
#   * gcloud authenticated as a user with run.invoker on the service
#     (`gcloud auth login`)
#   * .venv at zebra-hint-generator/.venv with gradio + requests installed

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

export QUERY_RAG_URL="https://query-rag-773402166266.us-central1.run.app"

for candidate in "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/../.venv/bin/python3"; do
  if [[ -x "$candidate" ]]; then PY="$candidate"; break; fi
done
PY="${PY:-$(command -v python3)}"

exec "$PY" test_frontend.py
