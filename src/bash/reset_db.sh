#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

"$PYTHON_BIN" -c "from src.db.init_db import reset_db; reset_db(); print('Database reset complete')"
