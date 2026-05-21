#!/usr/bin/env bash
# Bibliometric Analysis System v16 — one-click installer (Linux)
# Run: chmod +x installers/linux/install.sh && ./installers/linux/install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export BIBLIOMETRICS_ROOT="$ROOT"

bash "$ROOT/installers/common/install-core.sh"

echo
read -r -p "Launch the application now? [Y/n]: " RUN
if [[ ! "${RUN:-}" =~ ^[Nn]$ ]]; then
  exec "$ROOT/run.sh"
fi
