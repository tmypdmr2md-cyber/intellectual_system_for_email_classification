#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

LIMIT="${LIMIT:-5}"

curl -sS -X POST "$API_BASE_URL/processing/process-next?limit=$LIMIT"
echo
