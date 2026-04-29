#!/usr/bin/env bash
#
# Local launcher for test_frontend.py.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

exec python test_frontend.py
