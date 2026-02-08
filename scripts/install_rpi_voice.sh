#!/usr/bin/env bash
set -euo pipefail

# Install voice dependencies for nanobot on Raspberry Pi / Debian-like systems.
# Run from the repository root: scripts/install_rpi_voice.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Locate or build a compatible Python (3.9–3.11) for tflite-runtime/openwakeword.
find_py() {
  for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      local ver
      ver="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      case "$ver" in
        3.9|3.10|3.11)
          PY="$candidate"
          PY_VER="$ver"
          return 0
          ;;
      esac
    fi
  done
  return 1
}

if ! find_py; then
  echo "No compatible Python (3.9–3.11) found. Attempting pyenv install of 3.11.9..." >&2

  # Minimal build deps for pyenv Python build
  sudo apt-get update
  sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

  if [ ! -d "$HOME/.pyenv" ]; then
    curl https://pyenv.run | bash
  fi

  export PATH="$HOME/.pyenv/bin:$PATH"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init - 2>/dev/null || true)"

  pyenv install -s 3.11.9
  PY="$HOME/.pyenv/versions/3.11.9/bin/python"
  PY_VER="3.11"
fi

# System packages required for audio and scientific deps
sudo apt-get update

# Try atlas first; if unavailable (e.g., Debian trixie), fall back to openblas.
# Also attempt versioned dev/venv packages for the chosen interpreter when available.
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
