#!/usr/bin/env bash
set -euo pipefail

# Runtime matrix checks for local/CI usage.
# - Stable lane: Python 3.14.x (required)
# - Dev lane: Python 3.15 pre-release (allowed to fail)
# - Free-threaded lane: Python 3.14t (allowed to fail)

echo "[stable] Python 3.14 runtime guard"
uv run python -m pytest tests/runtime/test_python_runtime_guard.py -v

echo "[dev] Python 3.15 pre-release check (allowed to fail)"
if command -v python3.15 >/dev/null 2>&1; then
  python3.15 -V || true
  python3.15 -m pytest tests/runtime/test_python_runtime_guard.py -v || true
else
  echo "python3.15 not found, skip"
fi

echo "[free-threaded] Python 3.14t check (allowed to fail)"
if command -v python3.14t >/dev/null 2>&1; then
  python3.14t -V || true
  python3.14t -m pytest tests/runtime/test_python_runtime_guard.py -v || true
else
  echo "python3.14t not found, skip"
fi
