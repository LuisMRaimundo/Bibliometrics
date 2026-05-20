#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" "$ROOT/software_gui_pro_4.py"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/software_gui_pro_4.py"
fi

echo "Python not found. Run ./install.sh first."
exit 1
