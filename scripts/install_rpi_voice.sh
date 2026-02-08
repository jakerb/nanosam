#!/usr/bin/env bash
set -euo pipefail

# Install voice dependencies for nanobot on Raspberry Pi / Debian-like systems.
# Run from the repository root: scripts/install_rpi_voice.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Select a Python interpreter (prefer 3.12/3.11/3.10/3.9). tflite-runtime has wheels through 3.11 on Pi, and 2.14.0 supports 3.9–3.11.
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done

if [ -z "${PY:-}" ]; then
  echo "No python3 interpreter found. Install Python 3.10 or 3.11 and rerun." >&2
  exit 1
fi

PY_VER="$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PY_VER" in
  3.9|3.10|3.11) TFLITE_VERSION="2.14.0" ;;
  *)
    echo "Python $PY_VER is unsupported for tflite-runtime wheels on Pi. Please install Python 3.10 or 3.11." >&2
    exit 1
    ;;
esac

# System packages required for audio and scientific deps
sudo apt-get update

# Try atlas first; if unavailable (e.g., Debian trixie), fall back to openblas.
# Also attempt versioned dev/venv packages for the chosen interpreter.
if sudo apt-get install -y "python${PY_VER}-venv" "python${PY_VER}-dev" python3-venv python3-dev build-essential libatlas-base-dev portaudio19-dev libsndfile1; then
  :
else
  echo "libatlas-base-dev not available; falling back to libopenblas-dev" >&2
  sudo apt-get install -y "python${PY_VER}-venv" "python${PY_VER}-dev" python3-venv python3-dev build-essential libopenblas-dev portaudio19-dev libsndfile1
fi

# Create virtualenv
rm -rf .venv
"$PY" -m venv .venv

# Upgrade packaging tools
./.venv/bin/python -m pip install --upgrade pip wheel setuptools

# Install tflite-runtime explicitly (needed by openwakeword). Version chosen per Python version.
./.venv/bin/pip install "tflite-runtime==${TFLITE_VERSION}"

# Install nanobot with voice extras
./.venv/bin/pip install -e '.[voice]'

echo
echo "Voice install complete. Run the assistant with:"
echo "  $ROOT/.venv/bin/nanobot voice"
