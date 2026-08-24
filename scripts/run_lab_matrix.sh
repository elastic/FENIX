#!/usr/bin/env bash
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
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
