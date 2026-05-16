#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Portrait Split — One-command installer for Ubuntu
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/autopro-ug/portrait-split/main/install.sh)
#
# ═══════════════════════════════════════════════════════════════════
set -e

REPO="https://github.com/Dihfahsih1/portrait-split"
RAW="https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main"
INSTALL_DIR="$HOME/.portrait_split"
VERSION="2.0.0"

# ── Pretty print ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
echo ""
echo -e "${BLUE}${BOLD}"
echo "  ██████╗  ██████╗ ██████╗ ████████╗██████╗  █████╗ ██╗████████╗"
echo "  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██║╚══██╔══╝"
echo "  ██████╔╝██║   ██║██████╔╝   ██║   ██████╔╝███████║██║   ██║   "
echo "  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══██╗██╔══██║██║   ██║   "
echo "  ██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║██║  ██║██║   ██║   "
echo "  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝   "
echo ""
echo -e "  ${CYAN}  S P L I T     v${VERSION}${RESET}"
echo ""
echo -e "${RESET}  Face-tracked HD portrait video — like TikTok Smart Cut"
echo -e "  ${BLUE}${REPO}${RESET}"
echo ""
}

step() { echo -e "\n${CYAN}${BOLD}[$1/5]${RESET} $2"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
fail() { echo -e "  ${RED}✗ ERROR:${RESET} $1"; exit 1; }

banner

# ── Check Ubuntu ─────────────────────────────────────────────────
step 1 "Checking system"
[[ "$(uname)" == "Linux" ]] || fail "This installer is for Ubuntu/Linux only."
ok "Ubuntu Linux detected"

# ── System packages ───────────────────────────────────────────────
step 2 "Installing system dependencies (sudo required once)"
sudo apt-get update -qq
sudo apt-get install -y \
    ffmpeg \
    python3 \
    python3-venv \
    python3-full \
    python3-tk \
    curl \
    > /dev/null 2>&1
ok "ffmpeg installed"
ok "Python 3 + tkinter installed"

# ── Download scripts ──────────────────────────────────────────────
step 3 "Downloading Portrait Split"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

for f in portrait_split.py portrait_split_gui.py; do
    curl -fsSL "$RAW/$f" -o "$INSTALL_DIR/$f"
    ok "Downloaded $f"
done

# ── Python venv ───────────────────────────────────────────────────
step 4 "Setting up Python environment"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/python3" -m pip install --upgrade pip -q
"$INSTALL_DIR/venv/bin/python3" -m pip install opencv-python numpy -q
ok "Virtual environment ready"
ok "opencv-python + numpy installed"

# ── Launchers + desktop entry ─────────────────────────────────────
step 5 "Registering app"

# GUI launcher
cat > "$INSTALL_DIR/launch.sh" << 'SH'
#!/bin/bash
cd "$(dirname "$0")"
exec venv/bin/python3 portrait_split_gui.py "$@"
SH
chmod +x "$INSTALL_DIR/launch.sh"

# CLI launcher
cat > "$INSTALL_DIR/cli.sh" << 'SH'
#!/bin/bash
cd "$(dirname "$0")"
exec venv/bin/python3 portrait_split.py "$@"
SH
chmod +x "$INSTALL_DIR/cli.sh"

# /usr/local/bin symlinks
sudo ln -sf "$INSTALL_DIR/launch.sh" /usr/local/bin/portrait-split
sudo ln -sf "$INSTALL_DIR/cli.sh"    /usr/local/bin/portrait-split-cli
ok "Created: portrait-split  (GUI)"
ok "Created: portrait-split-cli  (terminal)"

# .desktop file for app menu
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/portrait-split.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Portrait Split
GenericName=Portrait Video Tool
Comment=Face-tracked HD portrait video — like TikTok Smart Cut
Exec=$INSTALL_DIR/launch.sh
Icon=video-x-generic
Terminal=false
Categories=AudioVideo;Video;
Keywords=portrait;video;tiktok;reframe;split;shorts;reels;
StartupNotify=true
DESKTOP
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
ok "Added to app menu: 'Portrait Split'"

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔════════════════════════════════════════════════╗"
echo "  ║                                                ║"
echo "  ║   ✅  Installation complete!                   ║"
echo "  ║                                                ║"
echo "  ║   Open the app:                                ║"
echo "  ║     portrait-split                             ║"
echo "  ║     — or search 'Portrait Split' in app menu   ║"
echo "  ║                                                ║"
echo "  ║   Use from terminal:                           ║"
echo "  ║     portrait-split-cli -i video.mp4            ║"
echo "  ║                                                ║"
echo "  ╚════════════════════════════════════════════════╝"
echo -e "${RESET}"
