#!/usr/bin/env bash
# SessionStart hook wrapper: resolve a Python 3 interpreter, then hand off to
# record_account.py. Always exits 0 — a missing/renamed interpreter must never
# block or error a session; it just means that session goes unattributed.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="$here/record_account.py"

run() { "$@" "$script" >/dev/null 2>&1 || true; exit 0; }

# Prefer python3 (canonical on macOS/Linux).
command -v python3 >/dev/null 2>&1 && run python3
# Fall back to `python` only if it is actually Python 3.
if command -v python >/dev/null 2>&1 \
   && python -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
  run python
fi
# Windows launcher: force Python 3.
command -v py >/dev/null 2>&1 && run py -3

exit 0
