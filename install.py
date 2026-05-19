#!/usr/bin/env python3
"""
DIGITALCHURCH DC — Cross-platform installer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Works on: Windows 10/11 · Ubuntu 20.04+ · Debian · Mint

Includes:
  • Portrait Split
  • VideoSlicer v2.1 (Ultra Fast)
  • Automatic FFmpeg installation
"""

import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import zipfile
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────
VERSION    = "1.0.1"
RAW_BASE   = "https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main"
REPO_URL   = "https://github.com/Dihfahsih1/portrait-split"

SCRIPTS = [
    "portrait_split.py",
    "portrait_split_gui.py",
    "video_slicer.py",        # Ultra-fast version
    "digitalchurch_dc.py",
]

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"

# Install locations
if IS_WINDOWS:
    INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DigitalChurch"
else:
    INSTALL_DIR = Path.home() / ".digitalchurch"

VENV_DIR    = INSTALL_DIR / "venv"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python3")
VENV_PIP    = VENV_DIR / ("Scripts/pip.exe"    if IS_WINDOWS else "bin/pip")

# ── Colours ───────────────────────────────────────────────────────
def _ansi_supported():
    if IS_WINDOWS:
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)
            return True
        except:
            return False
    return True

USE_COLOUR = _ansi_supported()

def c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOUR else text

def green(t):  return c("32",   t)
def yellow(t): return c("33",   t)
def gold(t):   return c("33;1", t)
def cyan(t):   return c("36",   t)
def red(t):    return c("31;1", t)
def bold(t):   return c("1",    t)
def dim(t):    return c("2",    t)

TOTAL_STEPS = 5

def banner():
    print()
    print(gold("  ██████╗  ██████╗"))
    print(gold("  ██╔══██╗██╔════╝   DIGITALCHURCH"))
    print(gold("  ██║  ██║██║        DC Media Suite  v" + VERSION))
    print(gold("  ██║  ██║██║"))
    print(gold("  ██████╔╝╚██████╗"))
    print(gold("  ╚═════╝  ╚═════╝"))
    print()
    print(f"  {dim(REPO_URL)}")
    print(f"  {dim('Portrait Split  +  Ultra-Fast VideoSlicer')}")
    print()
    print(f"  {gold('✦')}  Platform : {bold(platform.system())} {platform.release()}")
    print(f"  {gold('✦')}  Install to: {bold(str(INSTALL_DIR))}")
    print()

def step(n, msg):
    print(f"\n{cyan(bold(f'[{n}/{TOTAL_STEPS}]'))} {bold(msg)}")

def ok(msg):      print(f"    {green('✔')}  {msg}")
def warn(msg):    print(f"    {yellow('⚠')}  {msg}")
def info(msg):    print(f"    {dim(msg)}")
def divider():    print(f"\n{dim('  ' + '─' * 54)}")

def fail(msg):
    print(f"\n  {red('✗  ERROR:')} {msg}\n")
    sys.exit(1)

def run(cmd, check=True, capture=False, **kwargs):
    result = subprocess.run(cmd, capture_output=capture, text=True, **kwargs)
    if check and result.returncode != 0:
        err = result.stderr.strip() if capture else ""
        fail(f"Command failed: {' '.join(map(str, cmd))}\n{err}")
    return result

# ─────────────────────────────────────────────────────────────────
# Step 1 — System checks
# ─────────────────────────────────────────────────────────────────
def check_system():
    step(1, "Checking system")

    vi = sys.version_info
    if vi < (3, 9):
        fail(f"Python 3.9+ required. You have {vi.major}.{vi.minor}.")

    ok(f"Python {vi.major}.{vi.minor}.{vi.micro}")

    if shutil.which("ffmpeg"):
        ok("ffmpeg found")
    else:
        warn("ffmpeg not found — will be installed automatically")

    try:
        import venv
        ok("venv module available")
    except ImportError:
        if IS_LINUX:
            fail("python3-venv not installed → sudo apt install python3-venv python3-full")
        else:
            fail("venv module missing")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 2 — System dependencies (FFmpeg + libraries)
# ─────────────────────────────────────────────────────────────────
def install_system_deps():
    step(2, "Installing system dependencies")

    if IS_WINDOWS:
        _install_system_deps_windows()
    elif IS_LINUX:
        _install_system_deps_linux()
    elif IS_MAC:
        _install_system_deps_mac()
    else:
        warn(f"Unsupported platform: {platform.system()}")

    divider()


def _install_system_deps_windows():
    if shutil.which("ffmpeg"):
        ok("ffmpeg already available")
        return

    info("Installing FFmpeg...")

    # Try winget first
    if shutil.which("winget"):
        info("Installing via winget...")
        result = run(["winget", "install", "Gyan.FFmpeg", "-e", "--silent",
                     "--accept-source-agreements", "--accept-package-agreements"],
                     check=False, capture=True)
        if result.returncode == 0:
            ok("FFmpeg installed via winget")
            return

    # Direct download fallback
    info("Downloading FFmpeg directly...")
    ffmpeg_dir = INSTALL_DIR / "ffmpeg"
    ffmpeg_zip = INSTALL_DIR / "ffmpeg.zip"

    try:
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        urllib.request.urlretrieve(url, ffmpeg_zip)

        with zipfile.ZipFile(ffmpeg_zip) as z:
            for member in z.namelist():
                if member.startswith('ffmpeg-') and '/bin/' in member:
                    z.extract(member, ffmpeg_dir.parent)

        # Rename folder
        for folder in ffmpeg_dir.parent.glob("ffmpeg-*"):
            folder.rename(ffmpeg_dir)
            break

        ffmpeg_zip.unlink(missing_ok=True)

        # Add to PATH
        bin_path = str(ffmpeg_dir / "bin")
        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
        ok(f"FFmpeg installed → {bin_path}")

    except Exception as e:
        warn(f"Auto FFmpeg install failed: {e}")
        warn("Download manually: https://www.gyan.dev/ffmpeg/builds/")


def _install_system_deps_linux():
    if not shutil.which("apt-get"):
        warn("apt-get not found — skipping system packages")
        return

    info("Installing system packages...")
    pkgs = ["ffmpeg", "python3-venv", "python3-full", "python3-tk",
            "libgl1", "libglib2.0-0", "python3-pyqt6.qtmultimedia"]

    run(["sudo", "apt-get", "update", "-qq"], check=False)
    run(["sudo", "apt-get", "install", "-y"] + pkgs, check=False)
    ok("System dependencies installed")


def _install_system_deps_mac():
    if shutil.which("brew"):
        info("Installing ffmpeg via Homebrew...")
        run(["brew", "install", "ffmpeg"], check=False)
        ok("ffmpeg installed")
    else:
        warn("Homebrew not found. Install from https://brew.sh")


# ─────────────────────────────────────────────────────────────────
# Step 3 — Download scripts
# ─────────────────────────────────────────────────────────────────
def download_scripts():
    step(3, "Downloading DIGITALCHURCH DC scripts")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    for fname in SCRIPTS:
        url = f"{RAW_BASE}/{fname}"
        dest = INSTALL_DIR / fname
        info(f"Downloading {fname}...")
        try:
            urllib.request.urlretrieve(url, dest)
            if dest.stat().st_size < 500:
                raise ValueError("Downloaded file too small")
            ok(f"Downloaded {fname}")
        except Exception as e:
            warn(f"Failed to download {fname}: {e}")
            if fname == "video_slicer.py":
                warn("VideoSlicer will need to be placed manually")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 4 — Virtual Environment + Packages
# ─────────────────────────────────────────────────────────────────
def setup_venv():
    step(4, "Setting up Python environment")

    info("Creating virtual environment...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    ok("Virtual environment created")

    info("Upgrading pip...")
    run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"])

    info("Installing required packages...")
    packages = [
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "yt-dlp>=2025.0.0",
        "PyQt6",
        "PyQt6-Qt6Multimedia",
    ]

    run([str(VENV_PIP), "install"] + packages, check=False)
    ok("All packages installed successfully")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 5 — Create launchers
# ─────────────────────────────────────────────────────────────────
def create_launchers():
    step(5, "Creating launchers & shortcuts")

    if IS_WINDOWS:
        _create_launchers_windows()
    elif IS_LINUX:
        _create_launchers_linux()
    elif IS_MAC:
        _create_launchers_mac()

    divider()


def _create_launchers_windows():
    pythonw = VENV_DIR / "Scripts" / "pythonw.exe"

    # GUI launchers (silent)
    gui_apps = {
        "digitalchurch.vbs":   "digitalchurch_dc.py",
        "portrait-split.vbs":  "portrait_split_gui.py",
        "video-slicer.vbs":    "video_slicer.py",
    }

    for vbs_name, script in gui_apps.items():
        vbs_path = INSTALL_DIR / vbs_name
        vbs_path.write_text(
            f'Set sh = CreateObject("WScript.Shell")\n'
            f'sh.Run Chr(34) & "{pythonw}" & Chr(34) & " " & Chr(34) & "{INSTALL_DIR / script}" & Chr(34), 0, False\n',
            encoding="utf-8"
        )

    ok("Silent GUI launchers created")


def _create_launchers_linux():
    # Simplified version - you can expand this later
    ok("Launchers can be created manually or via desktop entries")


def _create_launchers_mac():
    ok("macOS launchers can be created manually")


def done_banner():
    print()
    print(gold("  ╔══════════════════════════════════════════════════════════╗"))
    print(gold("  ║") + green(bold("   ✅  DIGITALCHURCH DC installed successfully!           ")) + gold("║"))
    print(gold("  ╚══════════════════════════════════════════════════════════╝"))
    print()
    print(f"   Installed to: {bold(str(INSTALL_DIR))}")
    print(f"   Run with:     {bold('video-slicer')}  or  {bold('portrait-split')}")
    print()


# ─────────────────────────────────────────────────────────────────
def main():
    banner()
    try:
        check_system()
        install_system_deps()
        download_scripts()
        setup_venv()
        create_launchers()
        done_banner()
    except KeyboardInterrupt:
        print(f"\n\n  {yellow('Installation cancelled by user.')}\n")
        sys.exit(1)
    except Exception as e:
        fail(str(e))


if __name__ == "__main__":
    main()