#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#
#   DIGITALCHURCH DC — Linux installer entry point
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.sh)
#
#   This script ensures Python 3.9+ is present, then hands off to
#   install.py which handles the full cross-platform installation.
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
echo "  ██║  ██║██║"
echo "  ██║  ██║██║        Handing off to install.py..."
echo "  ██████╔╝╚██████╗"
echo -e "  ╚═════╝  ╚═════╝${RESET}"
echo ""

# ── Ensure Python 3.9+ is available ──────────────────────────────
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
    warn "Python 3.9+ not found — installing via apt..."
    command -v apt-get >/dev/null 2>&1 || fail "apt-get not found. Install Python 3.9+ manually then re-run."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-venv python3-full >/dev/null 2>&1
    PYTHON_BIN="python3"
    ok "Python installed"
fi

PYVER=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
ok "Python ${PYVER} (${PYTHON_BIN})"

# ── Ensure curl is available ──────────────────────────────────────
command -v curl >/dev/null 2>&1 || {
    warn "curl not found — installing..."
    sudo apt-get install -y curl >/dev/null 2>&1
}

# ── Get install.py ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/install.py" ]]; then
    INSTALL_PY="$SCRIPT_DIR/install.py"
    ok "Using local install.py"
else
    INSTALL_PY="$(mktemp /tmp/dc_install_XXXXXX.py)"
    echo -e "  ${DIM}Downloading install.py...${RESET}"
    curl -fsSL "$RAW/install.py" -o "$INSTALL_PY" \
        || fail "Could not download install.py. Check your internet connection."
    ok "install.py downloaded"
fi

# ── Hand off ──────────────────────────────────────────────────────
echo ""
exec "$PYTHON_BIN" "$INSTALL_PY" "$@"
