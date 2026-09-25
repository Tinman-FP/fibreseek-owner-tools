#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

python_bin="${PYTHON_BIN:-python3}"
if ! "${python_bin}" - <<'PY'
import tkinter as tk
raise SystemExit(0 if tk.TkVersion >= 8.6 else 1)
PY
then
  echo "A Python runtime with Tcl/Tk 8.6 or newer is required." >&2
  echo "On macOS with Homebrew: brew install python@3.11 python-tk@3.11" >&2
  echo "Then run: PYTHON_BIN=/opt/homebrew/bin/python3.11 ./scripts/build_desktop_app.sh" >&2
  exit 1
fi

rm -rf .build-venv
"${python_bin}" -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts/package_desktop.py
