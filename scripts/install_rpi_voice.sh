#!/usr/bin/env bash
set -euo pipefail

# Install voice dependencies for nanobot on Raspberry Pi / Debian-like systems.
# Run from the repository root: scripts/install_rpi_voice.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Select a Python interpreter (prefers 3.12, then 3.11, then python3)
if command -v python3.12 >/dev/null 2>&1; then
  PY=python3.12
elif command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
else
  PY=python3
fi

# System packages required for audio and scientific deps
sudo apt-get update

# Try atlas first; if unavailable (e.g., Debian trixie), fall back to openblas
if sudo apt-get install -y python3-venv python3-dev build-essential libatlas-base-dev portaudio19-dev libsndfile1; then
  :
else
  echo "libatlas-base-dev not available; falling back to libopenblas-dev" >&2
  sudo apt-get install -y python3-venv python3-dev build-essential libopenblas-dev portaudio19-dev libsndfile1
fi

# Create virtualenv
rm -rf .venv
"$PY" -m venv .venv

# Upgrade packaging tools
./.venv/bin/python -m pip install --upgrade pip wheel setuptools

# Install nanobot with voice extras
./.venv/bin/pip install -e '.[voice]'

echo
echo "Voice install complete. Run the assistant with:"
echo "  $ROOT/.venv/bin/nanobot voice"
