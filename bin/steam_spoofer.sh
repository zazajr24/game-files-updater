#!/bin/bash
# Steam Manifest Key Spoofer - Launcher
# Works on Linux and macOS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required"
    exit 1
fi

pip3 install rich pyfiglet 2>/dev/null

cd "$SCRIPT_DIR"
exec python3 tui.py "$@"
