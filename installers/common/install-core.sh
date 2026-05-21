#!/usr/bin/env bash
# Bibliometric Analysis System v16 — shared install logic (macOS and Linux)
set -euo pipefail

if [[ -z "${BIBLIOMETRICS_ROOT:-}" ]]; then
  BIBLIOMETRICS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
ROOT="$BIBLIOMETRICS_ROOT"
cd "$ROOT"

echo "============================================================"
echo " Bibliometric Analysis System v16 — Installer"
echo "============================================================"
echo

VENV_PY="$ROOT/.venv/bin/python"

find_python() {
  if [[ -x "$VENV_PY" ]]; then
    echo "$VENV_PY"
    return 0
  fi
  local cmd
  for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      if "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        command -v "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

install_system_python() {
  local uname_s
  uname_s="$(uname -s)"
  echo "Python 3.10+ not found. Attempting to install..."
  if [[ "$uname_s" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      brew install python@3.12
      return 0
    fi
    echo "Install Python from https://www.python.org/downloads/"
    echo "Or install Homebrew (https://brew.sh) and run this installer again."
    return 1
  fi
  if command -v apt-get >/dev/null 2>&1; then
    echo "Trying: sudo apt-get install python3 python3-venv python3-pip"
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python python-pip
    return 0
  fi
  echo "Install Python 3.10+ using your system package manager, then re-run the installer."
  return 1
}

PY="$(find_python || true)"
if [[ -z "${PY:-}" ]]; then
  install_system_python || exit 1
  PY="$(find_python || true)"
fi
if [[ -z "${PY:-}" ]]; then
  echo "Python 3.10+ is still not available."
  exit 1
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Creating virtual environment in .venv ..."
  "$PY" -m venv "$ROOT/.venv"
fi

echo "Upgrading pip..."
"$VENV_PY" -m pip install --upgrade pip

echo "Installing Bibliometric Analysis System and optional features..."
"$VENV_PY" -m pip install -e ".[network,dashboard,enrichment]"

echo
echo "============================================================"
echo " Installation complete!"
echo
echo " Start the application:"
echo "   ./run.sh"
echo "   (or: .venv/bin/python software_gui_pro_4.py)"
echo "============================================================"
