#!/bin/bash
cd "$(dirname "$0")"
chmod +x install.sh run.sh 2>/dev/null || true
./install.sh
echo
read -r -p "Press Enter to close this window..."
