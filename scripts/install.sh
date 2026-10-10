#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for review_python in python3 python; do
  if command -v "$review_python" >/dev/null 2>&1 && "$review_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    exec "$review_python" "$script_dir/install.py" "$@"
  fi
done
echo 'Python 3.11+ is required. Install it, enable PATH, and reopen the terminal.' >&2
exit 2
