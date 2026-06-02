#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "Health:"
curl -sS "$API_BASE_URL/health"
echo

echo "Ingest inbox:"
curl -sS -X POST "$API_BASE_URL/emails/ingest"
echo

echo "Process next ${LIMIT:-5}:"
curl -sS -X POST "$API_BASE_URL/processing/process-next?limit=${LIMIT:-5}"
echo

echo "Overview:"
curl -sS "$API_BASE_URL/db/overview"
echo
