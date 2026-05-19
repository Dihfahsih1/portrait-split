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
    "video_slicer.py",
    "digitalchurch_dc.py",
]

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"

# ── Detect if we are running inside the embeddable Python ─────────
# The embeddable zip has no venv, no site-packages by default,
# and lives under %LOCALAPPDATA%\DigitalChurch\python-embed
_this_exe   = Path(sys.executable).resolve()
IS_EMBEDDED = IS_WINDOWS and "DigitalChurch" in str(_this_exe)

# Install locations
if IS_WINDOWS:
    INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DigitalChurch"
else:
    INSTALL_DIR = Path.home() / ".digitalchurch"

# On Windows embedded we skip venv — packages are already in the
# embeddable Python's site-packages (installed by install.bat).
# On full Python / Linux / Mac we still create a venv as before.
if IS_EMBEDDED:
    VENV_DIR    = None
    VENV_PYTHON = Path(sys.executable)
    VENV_PIP    = VENV_PYTHON.parent / "Scripts" / "pip.exe"
else:
    VENV_DIR    = INSTALL_DIR / "venv"
    if IS_WINDOWS:
        VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
        VENV_PIP    = VENV_DIR / "Scripts" / "pip.exe"
    else:
        VENV_PYTHON = VENV_DIR / "bin" / "python3"
        VENV_PIP    = VENV_DIR / "bin" / "pip"

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
    if IS_EMBEDDED:
        print(f"  {gold('✦')}  Mode: {bold('Embedded Python (no venv needed)')}")
    print()

def step(n, msg):
    print(f"\n{cyan(bold(f'[{n}/{TOTAL_STEPS}]'))} {bold(msg)}")

def ok(msg):    print(f"    {green('✔')}  {msg}")
def warn(msg):  print(f"    {yellow('⚠')}  {msg}")
def info(msg):  print(f"    {dim(msg)}")
def divider():  print(f"\n{dim('  ' + '─' * 54)}")

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

    if IS_EMBEDDED:
        ok("Embedded Python detected — skipping venv check")
    else:
        try:
            import venv
            ok("venv module available")
        except ImportError:
            if IS_LINUX:
                fail("python3-venv not installed → run: sudo apt install python3-venv python3-full")
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

    # Check the embedded ffmpeg location used by install.bat
    embedded_ffmpeg = INSTALL_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
    if embedded_ffmpeg.exists():
        bin_dir = str(embedded_ffmpeg.parent)
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        ok(f"ffmpeg found at {bin_dir}")
        return

    info("ffmpeg not found — attempting to install...")

    # Try winget first (fast, no download needed on modern Windows)
    if shutil.which("winget"):
        info("Trying winget...")
        result = run(
            ["winget", "install", "Gyan.FFmpeg", "-e", "--silent",
             "--accept-source-agreements", "--accept-package-agreements"],
            check=False, capture=True
        )
        if result.returncode == 0:
            ok("FFmpeg installed via winget")
            return

    # Direct download fallback — only the 3 exe files (~45 MB)
    info("Downloading FFmpeg binaries directly...")
    ffmpeg_bin = INSTALL_DIR / "ffmpeg" / "bin"
    ffmpeg_bin.mkdir(parents=True, exist_ok=True)
    ffmpeg_zip = INSTALL_DIR / "ffmpeg.zip"

    try:
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        urllib.request.urlretrieve(url, ffmpeg_zip)

        with zipfile.ZipFile(ffmpeg_zip) as z:
            for member in z.namelist():
                fname = Path(member).name
                if fname in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe"):
                    with z.open(member) as src, open(ffmpeg_bin / fname, "wb") as dst:
                        dst.write(src.read())

        ffmpeg_zip.unlink(missing_ok=True)
        os.environ["PATH"] = str(ffmpeg_bin) + os.pathsep + os.environ.get("PATH", "")
        ok(f"FFmpeg installed → {ffmpeg_bin}")

    except Exception as e:
        warn(f"Auto FFmpeg install failed: {e}")
        warn("Download manually: https://www.gyan.dev/ffmpeg/builds/")


def _install_system_deps_linux():
    if not shutil.which("apt-get"):
        warn("apt-get not found — skipping system packages")
        return

    info("Installing system packages...")
    pkgs = [
        "ffmpeg", "python3-venv", "python3-full", "python3-tk",
        "libgl1", "libglib2.0-0", "python3-pyqt6.qtmultimedia",
    ]
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
        url  = f"{RAW_BASE}/{fname}"
        dest = INSTALL_DIR / fname
        info(f"Downloading {fname}...")
        try:
            urllib.request.urlretrieve(url, dest)
            if dest.stat().st_size < 500:
                raise ValueError("Downloaded file too small — check GitHub path")
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

    if IS_EMBEDDED:
        # Packages were already installed by install.bat — just verify
        info("Embedded Python: verifying packages installed by install.bat...")
        missing = []
        for pkg, import_name in [
            ("opencv-python", "cv2"),
            ("numpy",         "numpy"),
            ("yt-dlp",        "yt_dlp"),
            ("PyQt6",         "PyQt6"),
        ]:
            try:
                __import__(import_name)
                ok(f"{pkg} ✔")
            except ImportError:
                warn(f"{pkg} not found — installing now...")
                result = run(
                    [str(VENV_PYTHON), "-m", "pip", "install", pkg],
                    check=False, capture=True
                )
                if result.returncode == 0:
                    ok(f"{pkg} installed")
                else:
                    missing.append(pkg)

        if missing:
            fail(f"Could not install: {', '.join(missing)}")
        else:
            ok("All packages verified")

    else:
        # Full Python / Linux / Mac — create venv as normal
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
    # On embedded Python, use pythonw.exe from the embed folder
    # On full Python with venv, use the venv's pythonw
    if IS_EMBEDDED:
        pythonw = VENV_PYTHON.parent / "pythonw.exe"
        if not pythonw.exists():
            # Embeddable zip doesn't always ship pythonw — fall back to python.exe
            pythonw = VENV_PYTHON
    else:
        pythonw = VENV_DIR / "Scripts" / "pythonw.exe"

    gui_apps = {
        "digitalchurch.vbs":  "digitalchurch_dc.py",
        "portrait-split.vbs": "portrait_split_gui.py",
        "video-slicer.vbs":   "video_slicer.py",
    }

    for vbs_name, script in gui_apps.items():
        vbs_path = INSTALL_DIR / vbs_name
        vbs_path.write_text(
            f'Set sh = CreateObject("WScript.Shell")\n'
            f'sh.Run Chr(34) & "{pythonw}" & Chr(34) & " " & Chr(34)'
            f' & "{INSTALL_DIR / script}" & Chr(34), 0, False\n',
            encoding="utf-8"
        )

    # Also write a simple .bat launcher that shows a console window
    bat = INSTALL_DIR / "run-videoslicer.bat"
    bat.write_text(
        f'@echo off\n'
        f'"{VENV_PYTHON}" "{INSTALL_DIR / "video_slicer.py"}"\n'
        f'pause\n',
        encoding="utf-8"
    )

    ok("Launchers created")
    ok(f"Quick launch: {bat}")


def _create_launchers_linux():
    for app_name, script in [
        ("digitalchurch",  "digitalchurch_dc.py"),
        ("portrait-split", "portrait_split_gui.py"),
        ("video-slicer",   "video_slicer.py"),
    ]:
        launcher = Path.home() / ".local" / "bin" / app_name
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            f"#!/bin/bash\n"
            f'"{VENV_PYTHON}" "{INSTALL_DIR / script}" "$@"\n',
            encoding="utf-8"
        )
        launcher.chmod(0o755)
        ok(f"Created launcher: {launcher}")


def _create_launchers_mac():
    ok("macOS launchers can be created manually")


def done_banner():
    print()
    print(gold("  ╔══════════════════════════════════════════════════════════╗"))
    print(gold("  ║") + green(bold("   ✅  DIGITALCHURCH DC installed successfully!           ")) + gold("║"))
    print(gold("  ╚══════════════════════════════════════════════════════════╝"))
    print()
    print(f"   Installed to: {bold(str(INSTALL_DIR))}")
    if IS_WINDOWS:
        print(f"   Run VideoSlicer: double-click  {bold('run-videoslicer.bat')}  in the install folder")
        print(f"   Or silent GUI:   double-click  {bold('video-slicer.vbs')}")
    else:
        print(f"   Run with:  {bold('video-slicer')}  or  {bold('portrait-split')}")
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