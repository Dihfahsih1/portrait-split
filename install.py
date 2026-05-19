#!/usr/bin/env python3
"""
DIGITALCHURCH DC — Cross-platform installer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Works on: Windows 10/11 · Ubuntu 20.04+ · Debian · Mint

Usage:
  Windows  →  python install.py        (or double-click install.bat first)
  Linux    →  python3 install.py
"""

import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import urllib.error
import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────
VERSION    = "1.0.0"
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

# Install locations
if IS_WINDOWS:
    INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DigitalChurch"
else:
    INSTALL_DIR = Path.home() / ".digitalchurch"

VENV_DIR    = INSTALL_DIR / "venv"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python3")
VENV_PIP    = VENV_DIR / ("Scripts/pip.exe"    if IS_WINDOWS else "bin/pip")

# ── Colours (disabled on Windows if no ANSI support) ─────────────
def _ansi_supported():
    if IS_WINDOWS:
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            # Enable VIRTUAL_TERMINAL_PROCESSING (0x0004)
            kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)
            return True
        except Exception:
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
    print(f"  {dim('Includes: Portrait Split  +  VideoSlicer')}")
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
    """Run a command, stream output unless capture=True."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        **kwargs,
    )
    if check and result.returncode != 0:
        err = result.stderr.strip() if capture else ""
        fail(f"Command failed (exit {result.returncode}): {' '.join(str(c) for c in cmd)}\n{err}")
    return result

# ─────────────────────────────────────────────────────────────────
# Step 1 — System checks
# ─────────────────────────────────────────────────────────────────
def check_system():
    step(1, "Checking system")

    # Python version
    vi = sys.version_info
    if vi < (3, 9):
        fail(
            f"Python 3.9+ required — you have {vi.major}.{vi.minor}.\n"
            + ("    Download from https://www.python.org/downloads/" if IS_WINDOWS
               else "    Run: sudo apt install python3.11")
        )
    ok(f"Python {vi.major}.{vi.minor}.{vi.micro}")

    # ffmpeg
    if shutil.which("ffmpeg"):
        ok("ffmpeg found")
    else:
        if IS_WINDOWS:
            warn("ffmpeg not found — will attempt to install via winget")
        else:
            warn("ffmpeg not found — will install via apt")

    # pip / venv modules available in this Python?
    try:
        import venv  # noqa
        ok("venv module available")
    except ImportError:
        if IS_LINUX:
            fail("python3-venv not installed.\n    Run: sudo apt install python3-venv python3-full")
        else:
            fail("venv module missing from your Python installation.")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 2 — System dependencies (ffmpeg, system libs)
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
        warn(f"Unsupported platform: {platform.system()} — skipping system deps")

    divider()


def _install_system_deps_windows():
    # winget — available on Windows 10 1709+ and all Windows 11
    if shutil.which("winget"):
        info("Installing ffmpeg via winget…")
        result = run(
            ["winget", "install", "--id", "Gyan.FFmpeg",
             "-e", "--accept-source-agreements", "--accept-package-agreements",
             "--silent"],
            check=False, capture=True,
        )
        if result.returncode == 0:
            ok("ffmpeg installed via winget")
        else:
            warn(
                "winget install failed — download ffmpeg manually:\n"
                "    https://www.gyan.dev/ffmpeg/builds/\n"
                "    Extract and add the 'bin' folder to your PATH."
            )
    else:
        warn(
            "winget not available.\n"
            "    Download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/\n"
            "    Extract and add the 'bin' folder to your system PATH."
        )

    # Visual C++ Redistributable (needed by OpenCV)
    info("Checking Visual C++ Redistributable…")
    vc_path = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/vcruntime140.dll"
    if vc_path.exists():
        ok("Visual C++ Redistributable already installed")
    else:
        info("Downloading Visual C++ Redistributable…")
        vc_url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        vc_installer = INSTALL_DIR / "vc_redist.x64.exe"
        try:
            urllib.request.urlretrieve(vc_url, vc_installer)
            run([str(vc_installer), "/install", "/quiet", "/norestart"], check=False)
            ok("Visual C++ Redistributable installed")
        except Exception as e:
            warn(f"Could not install VC++ Redist automatically: {e}")


def _install_system_deps_linux():
    if not shutil.which("apt-get"):
        warn("apt-get not found — skipping system package install (non-Debian system?)")
        return

    info("Updating apt package lists…")
    run(["sudo", "apt-get", "update", "-qq"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    pkgs = [
        "ffmpeg",
        "python3-venv", "python3-full", "python3-tk",
        "libgl1", "libglib2.0-0",
    ]
    info(f"Installing: {' '.join(pkgs)}")
    run(["sudo", "apt-get", "install", "-y"] + pkgs,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok("ffmpeg + system libraries installed")

    # Try apt PyQt6 (best for multimedia)
    info("Trying apt install of PyQt6 + Qt6 Multimedia…")
    result = run(
        ["sudo", "apt-get", "install", "-y",
         "python3-pyqt6",
         "python3-pyqt6.qtmultimedia",
         "qml-module-qtmultimedia"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        ok("PyQt6 + Qt6Multimedia installed via apt")
        # Ensure INSTALL_DIR exists before writing the marker file
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        # Mark so venv uses --system-site-packages
        (INSTALL_DIR / ".apt_pyqt6").touch()
    else:
        warn("PyQt6 not available via apt — will use pip (no multimedia preview)")


def _install_system_deps_mac():
    if shutil.which("brew"):
        info("Installing ffmpeg via Homebrew…")
        run(["brew", "install", "ffmpeg"], check=False)
        ok("ffmpeg installed via Homebrew")
    else:
        warn(
            "Homebrew not found.\n"
            "    Install from https://brew.sh then run: brew install ffmpeg"
        )


# ─────────────────────────────────────────────────────────────────
# Step 3 — Download scripts
# ─────────────────────────────────────────────────────────────────
def download_scripts():
    step(3, "Downloading DIGITALCHURCH DC scripts")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    for fname in SCRIPTS:
        url  = f"{RAW_BASE}/{fname}"
        dest = INSTALL_DIR / fname
        info(f"Fetching {fname}…")
        try:
            urllib.request.urlretrieve(url, dest)
            if dest.stat().st_size < 100:
                raise ValueError("File too small — likely a 404 page")
            ok(f"Downloaded {fname}")
        except Exception as e:
            dest.unlink(missing_ok=True)
            if fname in ("video_slicer.py", "digitalchurch_dc.py"):
                warn(f"{fname} not in repo yet — place it manually in {INSTALL_DIR}")
            else:
                fail(f"Could not download {fname}: {e}")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 4 — Python virtual environment + pip packages
# ─────────────────────────────────────────────────────────────────
def setup_venv():
    step(4, "Setting up Python environment")

    use_system_site = (INSTALL_DIR / ".apt_pyqt6").exists()

    info("Creating virtual environment…")
    venv_cmd = [sys.executable, "-m", "venv"]
    if use_system_site:
        venv_cmd.append("--system-site-packages")
    venv_cmd.append(str(VENV_DIR))
    run(venv_cmd)
    ok(f"venv created {'(system-site-packages for PyQt6)' if use_system_site else ''}")

    info("Upgrading pip…")
    run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"])

    # Core packages for Portrait Split
    info("Installing opencv-python, numpy…")
    run([str(VENV_PIP), "install", "opencv-python", "numpy", "-q"])
    ok("opencv-python + numpy installed")

    # yt-dlp for VideoSlicer
    info("Installing yt-dlp…")
    run([str(VENV_PIP), "install", "yt-dlp", "-q"])
    ok("yt-dlp installed")

    # PyQt6 — only via pip if apt didn't handle it
    if not use_system_site:
        info("Installing PyQt6…")
        run([str(VENV_PIP), "install", "PyQt6", "-q"])
        ok("PyQt6 installed")

        info("Installing PyQt6-Qt6Multimedia (video preview support)…")
        result = run(
            [str(VENV_PIP), "install", "PyQt6-Qt6Multimedia", "-q"],
            check=False, capture=True,
        )
        if result.returncode == 0:
            ok("PyQt6-Qt6Multimedia installed")
        else:
            warn("PyQt6-Qt6Multimedia not available — video preview disabled in VideoSlicer")

    divider()


# ─────────────────────────────────────────────────────────────────
# Step 5 — Launchers + shortcuts
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


# ── Windows ───────────────────────────────────────────────────────

def _create_launchers_windows():
    bat = {
        "digitalchurch.bat": "digitalchurch_dc.py",
        "portrait-split.bat": "portrait_split_gui.py",
        "video-slicer.bat":   "video_slicer.py",
        "portrait-split-cli.bat": "portrait_split.py",
    }
    for bat_name, script in bat.items():
        bat_path = INSTALL_DIR / bat_name
        bat_path.write_text(
            f'@echo off\ncd /d "%~dp0"\nvenv\\Scripts\\python.exe {script} %*\n',
            encoding="utf-8",
        )
    ok("Created .bat launchers in install folder")

    # Start Menu shortcuts via PowerShell
    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/DigitalChurch DC"
    start_menu.mkdir(parents=True, exist_ok=True)

    shortcuts = [
        ("DIGITALCHURCH DC",  "digitalchurch_dc.py",      "🎬 DC Media Hub"),
        ("Portrait Split",    "portrait_split_gui.py",    "📐 Face-tracked portrait reframe"),
        ("VideoSlicer",       "video_slicer.py",          "✂ Precision video cutter"),
    ]

    ps_template = """
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{lnk}")
$Shortcut.TargetPath = "{python}"
$Shortcut.Arguments = '"{script}"'
$Shortcut.WorkingDirectory = "{wdir}"
$Shortcut.Description = "{desc}"
$Shortcut.Save()
"""
    python_path = str(VENV_PYTHON)
    created = 0
    for name, script, desc in shortcuts:
        lnk  = str(start_menu / f"{name}.lnk")
        scr  = str(INSTALL_DIR / script)
        ps   = ps_template.format(
            lnk=lnk, python=python_path, script=scr,
            wdir=str(INSTALL_DIR), desc=desc,
        )
        result = run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=False, capture=True,
        )
        if result.returncode == 0:
            created += 1

    if created:
        ok(f"Start Menu shortcuts created  →  {start_menu}")
    else:
        warn("Could not create Start Menu shortcuts — run the .bat files directly")

    # Add install dir to user PATH
    _add_to_path_windows()


def _add_to_path_windows():
    """Add INSTALL_DIR to the current user's PATH via registry."""
    info("Adding install folder to user PATH…")
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE,
        )
        try:
            current, _ = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            current = ""

        install_str = str(INSTALL_DIR)
        if install_str.lower() not in current.lower():
            new_path = f"{current};{install_str}" if current else install_str
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            ok(f"PATH updated — restart your terminal for 'digitalchurch' command to work")
        else:
            ok("Install folder already in PATH")
        winreg.CloseKey(key)
    except Exception as e:
        warn(f"Could not update PATH automatically: {e}\n"
             f"    Add manually: {INSTALL_DIR}")


# ── Linux ─────────────────────────────────────────────────────────

def _create_launchers_linux():
    launchers = {
        "launch_dc.sh":       "digitalchurch_dc.py",
        "launch_portrait.sh": "portrait_split_gui.py",
        "launch_slicer.sh":   "video_slicer.py",
        "cli.sh":             "portrait_split.py",
    }
    for sh_name, script in launchers.items():
        sh = INSTALL_DIR / sh_name
        sh.write_text(
            f'#!/bin/bash\ncd "$(dirname "$0")"\nexec venv/bin/python3 {script} "$@"\n'
        )
        sh.chmod(0o755)

    symlinks = {
        "/usr/local/bin/digitalchurch":       "launch_dc.sh",
        "/usr/local/bin/portrait-split":      "launch_portrait.sh",
        "/usr/local/bin/video-slicer":        "launch_slicer.sh",
        "/usr/local/bin/portrait-split-cli":  "cli.sh",
    }
    for link, sh_name in symlinks.items():
        run(["sudo", "ln", "-sf", str(INSTALL_DIR / sh_name), link], check=False)

    ok("Terminal commands: digitalchurch · portrait-split · video-slicer · portrait-split-cli")

    # Desktop entries
    apps_dir = Path.home() / ".local/share/applications"
    apps_dir.mkdir(parents=True, exist_ok=True)

    entries = [
        ("digitalchurch-dc",  "DIGITALCHURCH DC",  "launch_dc.sh",
         "Church Media Suite — Portrait reframe + Video slicer",
         "church;portrait;video;tiktok;reframe;youtube;slicer;"),
        ("portrait-split",    "Portrait Split",    "launch_portrait.sh",
         "Face-tracked HD portrait video — like TikTok Smart Cut",
         "portrait;video;tiktok;reframe;split;shorts;reels;"),
        ("video-slicer",      "VideoSlicer",       "launch_slicer.sh",
         "Precision video cutter — local files or YouTube, zero quality loss",
         "video;slicer;cutter;youtube;yt-dlp;ffmpeg;clip;trim;"),
    ]
    for de_name, app_name, launcher, comment, keywords in entries:
        de = apps_dir / f"{de_name}.desktop"
        de.write_text(
            f"[Desktop Entry]\nVersion=1.0\nType=Application\n"
            f"Name={app_name}\nComment={comment}\n"
            f"Exec={INSTALL_DIR / launcher}\nIcon=video-x-generic\n"
            f"Terminal=false\nCategories=AudioVideo;Video;\n"
            f"Keywords={keywords}\nStartupNotify=true\n"
        )
    run(["update-desktop-database", str(apps_dir)], check=False, capture=True)
    ok("App menu entries registered  (search 'DigitalChurch' in your launcher)")


# ── macOS ─────────────────────────────────────────────────────────

def _create_launchers_mac():
    apps = {
        "digitalchurch":     "digitalchurch_dc.py",
        "portrait-split":    "portrait_split_gui.py",
        "video-slicer":      "video_slicer.py",
        "portrait-split-cli":"portrait_split.py",
    }
    bin_dir = Path("/usr/local/bin")
    for cmd, script in apps.items():
        sh = INSTALL_DIR / f"{cmd}.sh"
        sh.write_text(
            f'#!/bin/bash\ncd "{INSTALL_DIR}"\nexec venv/bin/python3 {script} "$@"\n'
        )
        sh.chmod(0o755)
        link = bin_dir / cmd
        run(["sudo", "ln", "-sf", str(sh), str(link)], check=False)
    ok("Terminal commands installed to /usr/local/bin")


# ─────────────────────────────────────────────────────────────────
# Done banner
# ─────────────────────────────────────────────────────────────────

def done_banner():
    if IS_WINDOWS:
        launch_cmd = "digitalchurch"
        start_note = "— or find 'DIGITALCHURCH DC' in your Start Menu"
    elif IS_MAC:
        launch_cmd = "digitalchurch"
        start_note = "— restart your terminal first if command not found"
    else:
        launch_cmd = "digitalchurch"
        start_note = "— or search 'DIGITALCHURCH DC' in your app launcher"

    print()
    print(gold("  ╔══════════════════════════════════════════════════════════╗"))
    print(gold("  ║                                                          ║"))
    print(gold("  ║") + green(bold("   ✅  DIGITALCHURCH DC installed successfully!           ")) + gold("║"))
    print(gold("  ║                                                          ║"))
    print(gold("  ╠══════════════════════════════════════════════════════════╣"))
    print(gold("  ║                                                          ║"))
    print(gold("  ║") + f"   Open the DC hub:                                       " + gold("║"))
    print(gold("  ║") + f"     {bold(launch_cmd):<54}" + gold("║"))
    print(gold("  ║") + f"     {dim(start_note):<54}" + gold("║"))
    print(gold("  ║                                                          ║"))
    print(gold("  ║") + f"   Or run tools individually:                             " + gold("║"))
    print(gold("  ║") + f"     {bold('portrait-split'):<54}" + gold("║"))
    print(gold("  ║") + f"     {bold('video-slicer'):<54}" + gold("║"))
    print(gold("  ║") + f"     {bold('portrait-split-cli -i video.mp4'):<54}" + gold("║"))
    print(gold("  ║                                                          ║"))
    print(gold("  ╠══════════════════════════════════════════════════════════╣"))
    print(gold("  ║                                                          ║"))
    print(gold("  ║") + f"   Installed to: {dim(str(INSTALL_DIR)):<46}" + gold("║"))
    print(gold("  ║                                                          ║"))
    print(gold("  ╚══════════════════════════════════════════════════════════╝"))
    print()


# ─────────────────────────────────────────────────────────────────
# Entry point
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


if __name__ == "__main__":
    main()
