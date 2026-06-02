#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

BATCH_SIZE="${BATCH_SIZE:-20}"

curl -sS -X POST "$API_BASE_URL/processing/process-all?batch_size=$BATCH_SIZE"
echo
