#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#
#   DIGITALCHURCH DC — Linux Installer Bootstrap
#
#   Usage:
#     bash <(curl -fsSL https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.sh)
#
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

RAW="https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main"

RED='\033[0;31m'; GREEN='\033[0;32m'; GOLD='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✔${RESET}  $1"; }
warn() { echo -e "  ${GOLD}⚠${RESET}  $1"; }
fail() { echo -e "\n  ${RED}${BOLD}✗  ERROR:${RESET} $1\n"; exit 1; }

echo ""
echo -e "${GOLD}${BOLD}"
echo "  ██████╗  ██████╗    DIGITALCHURCH DC"
echo "  ██╔══██╗██╔════╝   Linux Bootstrap"
echo "  ██║  ██║██║        Ultra-Fast VideoSlicer Ready"
echo "  ██████╔╝╚██████╗"
echo -e "  ╚═════╝  ╚═════╝${RESET}"
echo ""

# ── Ensure Python 3.9+ ───────────────────────────────────────────
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" &>/dev/null; then
        VER_OK=$("$candidate" -c "import sys; print('ok' if sys.version_info>=(3,9) else 'old')" 2>/dev/null || echo "old")
        if [[ "$VER_OK" == "ok" ]]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    warn "Python 3.9+ not found. Installing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-venv python3-full python3-tk
        PYTHON_BIN="python3"
        ok "Python 3 installed via apt"
    else
        fail "Python 3.9+ not found and apt-get is unavailable. Please install Python manually."
    fi
fi

PYVER=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
ok "Using Python ${PYVER} (${PYTHON_BIN})"

# ── Ensure FFmpeg is installed (important for VideoSlicer) ───────
if ! command -v ffmpeg >/dev/null 2>&1; then
    warn "FFmpeg not found — installing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y ffmpeg
        ok "FFmpeg installed"
    else
        warn "Could not install FFmpeg automatically. VideoSlicer may have limited functionality."
    fi
else
    ok "FFmpeg found"
fi

# ── Ensure curl is available ─────────────────────────────────────
if ! command -v curl >/dev/null 2>&1; then
    warn "curl not found — installing..."
    sudo apt-get install -y curl
fi

# ── Download or use local install.py ─────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || echo "$PWD")"

if [[ -f "$SCRIPT_DIR/install.py" ]]; then
    INSTALL_PY="$SCRIPT_DIR/install.py"
    ok "Using local install.py"
else
    INSTALL_PY="$(mktemp /tmp/dc_install_XXXXXX.py)"
    echo -e "  ${DIM}Downloading latest install.py...${RESET}"
    curl -fsSL "$RAW/install.py" -o "$INSTALL_PY" || fail "Failed to download install.py"
    ok "install.py downloaded"
fi

# ── Final handoff ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}Starting full installation...${RESET}"
exec "$PYTHON_BIN" "$INSTALL_PY" "$@"