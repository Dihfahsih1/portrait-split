@echo off
:: ═══════════════════════════════════════════════════════════════
::   DIGITALCHURCH DC — Windows Installer (Fixed venv + FFmpeg)
::   This version properly enables venv in embeddable Python
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: Self-elevate to Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

cls
echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|     DIGITALCHURCH DC  —  Windows Installer              ^|
echo  ^|     Portrait Split  +  Ultra-Fast VideoSlicer           ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.
echo  [OK] Running as Administrator
echo.

:: ── Paths ─────────────────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"
set "EMBED_DIR=%INSTALL_DIR%\python-embed"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "PYTHON_BIN=%EMBED_DIR%\python.exe"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── Step 1: Python Setup ───────────────────────────────────────
echo  [1/5] Setting up Python...

if exist "%PYTHON_BIN%" (
    echo  [OK] Portable Python already installed
    goto :ffmpeg
)

echo  Downloading portable Python 3.11...
curl.exe -fsSL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -o "%TEMP%\pyembed.zip"
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%TEMP%\pyembed.zip'"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%TEMP%\pyembed.zip' -DestinationPath '%EMBED_DIR%' -Force"
del "%TEMP%\pyembed.zip" >nul 2>&1

:: === CRITICAL FIXES FOR EMBEDDABLE PYTHON ===
echo import site >> "%EMBED_DIR%\python311._pth"

:: Enable pip and venv
"%PYTHON_BIN%" -m ensurepip --upgrade --quiet

echo  [OK] Python ready

:: ── Step 2: FFmpeg ─────────────────────────────────────────────
:ffmpeg
echo.
echo  [2/5] Setting up FFmpeg...

if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg already installed
    goto :pip
)

echo  Downloading FFmpeg...
curl.exe -fsSL "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "%TEMP%\ffmpeg.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive '%TEMP%\ffmpeg.zip' '%TEMP%\ffmpeg_temp' -Force"

for /d %%d in ("%TEMP%\ffmpeg_temp\ffmpeg-*") do xcopy "%%d" "%FFMPEG_DIR%" /E /I /Y >nul
rd /s /q "%TEMP%\ffmpeg_temp" >nul 2>&1
del "%TEMP%\ffmpeg.zip" >nul 2>&1

set "PATH=%FFMPEG_DIR%\bin;%PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"[Environment]::SetEnvironmentVariable('Path', \"$env:Path;%FFMPEG_DIR%\bin\", [EnvironmentVariableTarget]::User)"

echo  [OK] FFmpeg installed

:: ── Step 3: Install Packages ───────────────────────────────────
:pip
echo.
echo  [3/5] Installing Python packages...

"%PYTHON_BIN%" -m pip install --upgrade pip --quiet
"%PYTHON_BIN%" -m pip install PyQt6 PyQt6-Qt6 yt-dlp opencv-python numpy --quiet

echo  [OK] Packages installed

:: ── Step 4: Run main installer ─────────────────────────────────
echo.
echo  [4/5] Running main installer...

if exist "%~dp0install.py" (
    "%PYTHON_BIN%" "%~dp0install.py"
) else (
    echo  Downloading latest install.py...
    curl.exe -fsSL "https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py" -o "%TEMP%\dc_install.py"
    "%PYTHON_BIN%" "%TEMP%\dc_install.py"
    del "%TEMP%\dc_install.py" >nul 2>&1
)

echo.
echo  ========================================================
echo  Installation Completed Successfully!
echo  You can now run VideoSlicer.
echo  ========================================================
echo.
pause
exit /b 0