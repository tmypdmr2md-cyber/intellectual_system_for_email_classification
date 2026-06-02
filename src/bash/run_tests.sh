#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/email_classifier_pycache}" \
  "$PYTHON_BIN" -m unittest discover -s src/tests -p "test_*.py"
