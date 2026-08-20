#!/usr/bin/env bash
# Full lab matrix: core (user) + full (sudo) + cleanup. Uses venv fenix explicitly.
# Safe to run in that order: the matrix unlinks /dev/shm objects and does not
# delete bin/fenix-memfd-self-reexec. If you already hand-ran those techniques:
#   make helpers && "$FENIX" cleanup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export FENIX_BIN_DIR="${FENIX_BIN_DIR:-$ROOT/bin}"
FENIX="${FENIX:-$ROOT/.venv/bin/fenix}"

if [[ ! -x "$FENIX" ]]; then
  echo "Missing $FENIX — run: pip install -e ." >&2
  exit 1
fi

echo "=== fenix run-all (core) ==="
"$FENIX" -q run-all --no-explain

echo ""
echo "=== fenix run-all --full (sudo) ==="
sudo env FENIX_BIN_DIR="$FENIX_BIN_DIR" "$FENIX" -q run-all --full --no-explain

echo ""
echo "=== fenix cleanup ==="
"$FENIX" -q cleanup
sudo env FENIX_BIN_DIR="$FENIX_BIN_DIR" "$FENIX" -q cleanup -t lkm-load 2>/dev/null || true

echo ""
echo "Lab matrix finished."
