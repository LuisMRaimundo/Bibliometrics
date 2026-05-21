#!/bin/bash
# Bibliometric Analysis System v16 — one-click installer (macOS)
# Double-click in Finder, or: chmod +x installers/macos/INSTALL.command && ./installers/macos/INSTALL.command
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

chmod +x installers/linux/install.sh installers/common/install-core.sh run.sh 2>/dev/null || true

export BIBLIOMETRICS_ROOT="$ROOT"
bash "$ROOT/installers/common/install-core.sh"

echo
read -r -p "Launch the application now? [Y/n]: " RUN
if [[ ! "${RUN:-}" =~ ^[Nn]$ ]]; then
  if [[ -x "$ROOT/run.sh" ]]; then
    exec "$ROOT/run.sh"
  else
    exec "$ROOT/.venv/bin/python" "$ROOT/software_gui_pro_4.py"
  fi
fi

echo
read -r -p "Press Enter to close this window..."
