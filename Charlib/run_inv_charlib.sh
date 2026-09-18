#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

charlib_python="${CHARLIB_PYTHON:-/foss/tools/charlib/bin/python}"
if [[ -n "${CHARLIB_NUMPY_DIR:-}" ]]; then
    export PYTHONPATH="$CHARLIB_NUMPY_DIR${PYTHONPATH:+:$PYTHONPATH}"
fi
"$charlib_python" -c 'import numpy; print("CharLib NumPy:", numpy.__version__, numpy.__file__)'
"$charlib_python" /foss/tools/charlib/bin/charlib run Charlib/inv.yaml --output Charlib

grep -q 'cell (inv)' Charlib/inv.lib
grep -Ei 'function.*(!VIN|VIN.*\x27)' Charlib/inv.lib > /dev/null
grep -q 'index_1.*0.01.*0.1.*1' Charlib/inv.lib
grep -q 'index_2.*0.0005.*0.01.*0.1' Charlib/inv.lib

printf 'Validated Charlib/inv.lib\n'
