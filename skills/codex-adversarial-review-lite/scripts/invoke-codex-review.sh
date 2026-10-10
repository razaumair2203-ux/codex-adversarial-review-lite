#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
bundle=${1:?Pass bundle path}
result=${2:?Pass result path}
shift 2
args=(run --backend codex --bundle "$bundle" --result "$result")
# Historical third positional model remains accepted; other options use named flags.
if [[ $# -gt 0 && "$1" != --* ]]; then args+=(--model "$1"); shift; fi
for review_python in python3 python; do
  if command -v "$review_python" >/dev/null 2>&1 && "$review_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    exec "$review_python" "$script_dir/review_runner.py" "${args[@]}" "$@"
  fi
done
echo 'Python 3.11+ is required. Install it, enable PATH, and reopen the terminal.' >&2
printf '%s\n' '{"result":"setup_needed","verdict":null,"errors":"Python 3.11+ is required."}' > "$result"
exit 2
