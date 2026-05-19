#!/usr/bin/env python3
"""
DIGITALCHURCH DC — Cross-platform installer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Works on: Windows 10/11 · Ubuntu 20.04+ · Debian · Mint

Includes:
  • Portrait Split
  • VideoSlicer v2.1 (Ultra Fast)
  • Automatic FFmpeg installation
  • Desktop & Start Menu shortcuts
"""

import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import zipfile
import tempfile
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
_this_exe   = Path(sys.executable).resolve()
IS_EMBEDDED = IS_WINDOWS and "DigitalChurch" in str(_this_exe)

# Install locations
if IS_WINDOWS:
    INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DigitalChurch"
else:
    INSTALL_DIR = Path.home() / ".digitalchurch"

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

    embedded_ffmpeg = INSTALL_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
    if embedded_ffmpeg.exists():
        bin_dir = str(embedded_ffmpeg.parent)
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        ok(f"ffmpeg found at {bin_dir}")
        return

    info("ffmpeg not found — attempting to install...")

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
# Step 5 — Create launchers & shortcuts
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


def _create_windows_shortcut(target_path, shortcut_path, arguments="", working_dir="", 
                              description="", icon_path=""):
    """Create a Windows shortcut (.lnk file)"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.Targetpath = str(target_path)
        
        if arguments:
            shortcut.Arguments = arguments
        if working_dir:
            shortcut.WorkingDirectory = str(working_dir)
        if description:
            shortcut.Description = description
        if icon_path and Path(icon_path).exists():
            shortcut.IconLocation = str(icon_path)
            
        shortcut.save()
        return True
    except ImportError:
        # Fallback method using PowerShell
        try:
            ps_script = f"""
            $WshShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
            $Shortcut.TargetPath = '{target_path}'
            $Shortcut.Arguments = '{arguments}'
            $Shortcut.WorkingDirectory = '{working_dir}'
            $Shortcut.Description = '{description}'
            """
            if icon_path and Path(icon_path).exists():
                ps_script += f"\n$Shortcut.IconLocation = '{icon_path}'"
            ps_script += "\n$Shortcut.Save()"
            
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", 
                           "-Command", ps_script], capture_output=True, check=True)
            return True
        except Exception as e:
            warn(f"PowerShell shortcut creation failed: {e}")
            return False
    except Exception as e:
        warn(f"Shortcut creation failed: {e}")
        return False


def _create_launchers_windows():
    """Create Windows launchers and shortcuts"""
    
    # Get the python executable for launching
    if IS_EMBEDDED:
        pythonw = VENV_PYTHON.parent / "pythonw.exe"
        if not pythonw.exists():
            pythonw = VENV_PYTHON  # Fallback to python.exe if pythonw.exe not found
        python_exe = VENV_PYTHON  # For shortcuts, use python.exe
    else:
        pythonw = VENV_DIR / "Scripts" / "pythonw.exe"
        python_exe = VENV_PYTHON
    
    # Create VBS launchers (silent, no console window)
    gui_apps = {
        "digitalchurch.vbs":  "digitalchurch_dc.py",
        "portrait-split.vbs": "portrait_split_gui.py",
        "video-slicer.vbs":   "video_slicer.py",
    }

    for vbs_name, script in gui_apps.items():
        vbs_path = INSTALL_DIR / vbs_name
        script_path = INSTALL_DIR / script
        vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strPython = "{pythonw}"
strScript = "{script_path}"
strArgs = ""

If FSO.FileExists(strPython) Then
    WshShell.Run Chr(34) & strPython & Chr(34) & " " & Chr(34) & strScript & Chr(34) & strArgs, 0, False
Else
    MsgBox "Python not found: " & strPython, 16, "DigitalChurch DC Error"
End If
"""
        vbs_path.write_text(vbs_content, encoding="utf-8")
        ok(f"Created VBS launcher: {vbs_name}")

    # Create batch launchers (with console for debugging)
    bat_apps = {
        "VideoSlicer (Console)": "video_slicer.py",
        "Portrait Split (Console)": "portrait_split.py",
    }
    
    for bat_name, script in bat_apps.items():
        bat_filename = bat_name.replace(" ", "-").lower() + ".bat"
        bat_path = INSTALL_DIR / bat_filename
        bat_content = f"""@echo off
title {bat_name}
echo Starting {bat_name}...
echo.
"{python_exe}" "{INSTALL_DIR / script}" %*
if %errorlevel% neq 0 pause
"""
        bat_path.write_text(bat_content, encoding="utf-8")
        ok(f"Created batch launcher: {bat_filename}")

    # Create uninstall script
    _create_uninstall_script()
    
    # Try to install winshell for proper shortcut creation
    info("Setting up shortcut creation...")
    try:
        import win32com.client
        ok("win32com available")
    except ImportError:
        info("Installing pywin32 for shortcut creation...")
        run([str(VENV_PIP if not IS_EMBEDDED else str(VENV_PYTHON) + " -m pip"), 
             "install", "pywin32", "winshell"], check=False, capture=True)
    
    # Create Windows shortcuts
    info("Creating Desktop and Start Menu shortcuts...")
    _create_windows_shortcuts_all(python_exe)
    
    # Add FFmpeg to PATH permanently if needed
    ffmpeg_bin = INSTALL_DIR / "ffmpeg" / "bin"
    if ffmpeg_bin.exists():
        _add_to_path(ffmpeg_bin)


def _create_windows_shortcuts_all(python_exe):
    """Create all Windows shortcuts"""
    
    # Define shortcut locations
    desktop = Path.home() / "Desktop"
    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    dc_start_menu = start_menu / "DigitalChurch DC"
    dc_start_menu.mkdir(parents=True, exist_ok=True)
    
    # Check if public desktop is needed (all users)
    public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
    
    # Shortcut definitions
    shortcuts = {
        "DigitalChurch DC Suite": {
            "script": "digitalchurch_dc.py",
            "description": "DigitalChurch DC Media Suite - Complete toolkit for media processing",
            "all_users": False
        },
        "Portrait Split GUI": {
            "script": "portrait_split_gui.py",
            "description": "Quick and easy portrait video splitter",
            "all_users": False
        },
        "VideoSlicer Ultra Fast": {
            "script": "video_slicer.py",
            "description": "Ultra-fast video slicer with frame-accurate cutting and scene detection",
            "all_users": False
        }
    }
    
    created_count = 0
    
    for name, config in shortcuts.items():
        script_path = INSTALL_DIR / config["script"]
        
        if not script_path.exists():
            warn(f"Script not found, skipping shortcut: {script_path}")
            continue
        
        # Create Desktop shortcut
        desktop_shortcut = desktop / f"{name}.lnk"
        if _create_windows_shortcut(
            target_path=python_exe,
            shortcut_path=desktop_shortcut,
            arguments=f'"{script_path}"',
            working_dir=INSTALL_DIR,
            description=config["description"]
        ):
            ok(f"Desktop shortcut: {name}")
            created_count += 1
        
        # Create Start Menu shortcut
        start_shortcut = dc_start_menu / f"{name}.lnk"
        if _create_windows_shortcut(
            target_path=python_exe,
            shortcut_path=start_shortcut,
            arguments=f'"{script_path}"',
            working_dir=INSTALL_DIR,
            description=config["description"]
        ):
            created_count += 1
    
    # Create uninstall shortcut in Start Menu
    uninstall_script = INSTALL_DIR / "uninstall.bat"
    if uninstall_script.exists():
        uninstall_shortcut = dc_start_menu / "Uninstall DigitalChurch DC.lnk"
        if _create_windows_shortcut(
            target_path=uninstall_script,
            shortcut_path=uninstall_shortcut,
            working_dir=INSTALL_DIR,
            description="Uninstall DigitalChurch DC Media Suite"
        ):
            ok("Start Menu: Uninstall shortcut")
            created_count += 1
    
    # Create Documentation shortcut
    readme_path = INSTALL_DIR / "README.md"
    if readme_path.exists():
        docs_shortcut = dc_start_menu / "Documentation.lnk"
        _create_windows_shortcut(
            target_path=readme_path,
            shortcut_path=docs_shortcut,
            description="DigitalChurch DC Documentation"
        )
    
    if created_count > 0:
        ok(f"Created {created_count} shortcuts successfully")
    else:
        warn("No shortcuts were created - check permissions")


def _add_to_path(directory):
    """Add a directory to the user's PATH environment variable permanently"""
    try:
        import winreg
        
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                            "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            path, _ = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            path = ""
        
        if str(directory) not in path:
            new_path = f"{path};{directory}" if path else str(directory)
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            ok(f"Added to PATH: {directory}")
        
        winreg.CloseKey(key)
    except Exception as e:
        warn(f"Could not add to PATH: {e}")


def _create_uninstall_script():
    """Create uninstall batch script"""
    uninstall_bat = INSTALL_DIR / "uninstall.bat"
    
    # Escape backslashes for batch file
    install_dir_bat = str(INSTALL_DIR)
    appdata = os.environ.get("APPDATA", "")
    
    uninstall_content = f"""@echo off
title Uninstall DigitalChurch DC
color 0E
echo.
echo  ============================================================
echo    DigitalChurch DC - Uninstall
echo  ============================================================
echo.
echo  This will remove all DigitalChurch DC files and shortcuts.
echo.
choice /C YN /M "Are you sure you want to continue"
if errorlevel 2 goto :cancel
if errorlevel 1 goto :uninstall

:uninstall
echo.
echo  Removing shortcuts...

:: Remove Desktop shortcuts
if exist "%USERPROFILE%\\Desktop\\DigitalChurch DC Suite.lnk" del /q "%USERPROFILE%\\Desktop\\DigitalChurch DC Suite.lnk"
if exist "%USERPROFILE%\\Desktop\\Portrait Split GUI.lnk" del /q "%USERPROFILE%\\Desktop\\Portrait Split GUI.lnk"
if exist "%USERPROFILE%\\Desktop\\VideoSlicer Ultra Fast.lnk" del /q "%USERPROFILE%\\Desktop\\VideoSlicer Ultra Fast.lnk"

:: Remove Start Menu folder
if exist "{appdata}\\Microsoft\\Windows\\Start Menu\\Programs\\DigitalChurch DC" rmdir /s /q "{appdata}\\Microsoft\\Windows\\Start Menu\\Programs\\DigitalChurch DC"

echo  Removing from PATH...
:: Remove FFmpeg from PATH
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$path=[Environment]::GetEnvironmentVariable('Path','User'); $path=($path -replace [regex]::Escape('{install_dir_bat}\\ffmpeg\\bin;'),'').TrimEnd(';'); [Environment]::SetEnvironmentVariable('Path',$path,'User')"

echo  Removing installation directory...
rmdir /s /q "{install_dir_bat}"

if exist "{install_dir_bat}" (
    echo.
    echo  [WARNING] Could not remove everything.
    echo  Some files may be in use. Please close all DC applications and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    DigitalChurch DC has been uninstalled successfully!
echo  ============================================================
echo.
echo  Press any key to exit...
pause >nul
exit /b 0

:cancel
echo.
echo  Uninstall cancelled.
echo.
pause
exit /b 0
"""
    uninstall_bat.write_text(uninstall_content, encoding="utf-8")
    ok("Uninstall script created")


def _create_launchers_linux():
    """Create Linux desktop shortcuts and launchers"""
    
    # Create executable scripts in ~/.local/bin
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    
    for app_name, script in [
        ("digitalchurch",  "digitalchurch_dc.py"),
        ("portrait-split", "portrait_split_gui.py"),
        ("video-slicer",   "video_slicer.py"),
    ]:
        launcher = local_bin / app_name
        launcher.write_text(
            f"#!/bin/bash\n"
            f'exec "{VENV_PYTHON}" "{INSTALL_DIR / script}" "$@"\n',
            encoding="utf-8"
        )
        launcher.chmod(0o755)
        ok(f"Created launcher: {launcher}")
    
    # Create .desktop files for application menus
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    desktop_entries = {
        "digitalchurch-dc.desktop": {
            "name": "DigitalChurch DC Suite",
            "script": "digitalchurch_dc.py",
            "comment": "DigitalChurch DC Media Suite",
            "categories": "AudioVideo;Video;",
        },
        "portrait-split.desktop": {
            "name": "Portrait Split",
            "script": "portrait_split_gui.py",
            "comment": "Split portrait videos",
            "categories": "AudioVideo;Video;",
        },
        "video-slicer.desktop": {
            "name": "VideoSlicer Ultra Fast",
            "script": "video_slicer.py",
            "comment": "Ultra-fast video slicer",
            "categories": "AudioVideo;Video;",
        },
    }
    
    for desktop_file, config in desktop_entries.items():
        desktop_path = desktop_dir / desktop_file
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={config['name']}
Comment={config['comment']}
Exec={VENV_PYTHON} {INSTALL_DIR / config['script']}
Icon=video-player
Terminal=false
Categories={config['categories']}
StartupNotify=true
"""
        desktop_path.write_text(desktop_content, encoding="utf-8")
        desktop_path.chmod(0o755)
        ok(f"Created desktop entry: {desktop_file}")


def _create_launchers_mac():
    """Create macOS launchers"""
    apps_dir = Path.home() / "Applications" / "DigitalChurch DC"
    apps_dir.mkdir(parents=True, exist_ok=True)
    
    for app_name, script in [
        ("DigitalChurch DC Suite", "digitalchurch_dc.py"),
        ("Portrait Split", "portrait_split_gui.py"),
        ("VideoSlicer", "video_slicer.py"),
    ]:
        app_bundle = apps_dir / f"{app_name}.app"
        macos_dir = app_bundle / "Contents" / "MacOS"
        macos_dir.mkdir(parents=True, exist_ok=True)
        
        # Create launcher script
        launcher = macos_dir / app_name
        launcher.write_text(
            f"#!/bin/bash\n"
            f'exec "{VENV_PYTHON}" "{INSTALL_DIR / script}" "$@"\n',
            encoding="utf-8"
        )
        launcher.chmod(0o755)
        
        # Create Info.plist
        plist = app_bundle / "Contents" / "Info.plist"
        plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{VERSION}</string>
</dict>
</plist>""")
        
        ok(f"Created macOS app: {app_bundle}")


def done_banner():
    print()
    print(gold("  ╔══════════════════════════════════════════════════════════╗"))
    print(gold("  ║") + green(bold("   ✅  DIGITALCHURCH DC installed successfully!           ")) + gold("║"))
    print(gold("  ╚══════════════════════════════════════════════════════════╝"))
    print()
    print(f"   Installed to: {bold(str(INSTALL_DIR))}")
    print()
    if IS_WINDOWS:
        print(f"   {bold('Desktop Shortcuts:')}")
        print(f"     • DigitalChurch DC Suite")
        print(f"     • Portrait Split GUI")
        print(f"     • VideoSlicer Ultra Fast")
        print()
        print(f"   {bold('Start Menu:')}")
        print(f"     • All applications in 'DigitalChurch DC' folder")
        print(f"     • Uninstall shortcut included")
        print()
        print(f"   {bold('Quick Launch:')}")
        print(f"     • Double-click desktop shortcuts")
        print(f"     • Or run .bat files in install folder for console mode")
    else:
        print(f"   {bold('Launch with:')}")
        print(f"     • video-slicer")
        print(f"     • portrait-split")
        print(f"     • digitalchurch")
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