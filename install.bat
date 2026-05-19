@echo off
:: ═══════════════════════════════════════════════════════════════
::   DIGITALCHURCH DC — Windows Installer (with FFmpeg)
::   Includes: Python + FFmpeg + All dependencies
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: Self-elevate to Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue"

cls
echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|   DIGITALCHURCH DC  --  Windows Installer               ^|
echo  ^|   Portrait Split  +  VideoSlicer  +  FFmpeg             ^|
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
set "EMBED_ZIP=%TEMP%\dc_python_%RANDOM%.zip"
set "GETPIP=%TEMP%\dc_getpip_%RANDOM%.py"
set "INSTALL_PY=%TEMP%\dc_install_%RANDOM%.py"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── Step 1: Python ─────────────────────────────────────────────
echo  [1/5] Setting up Python...

if exist "%PYTHON_BIN%" (
    echo  [OK] Portable Python already installed
    goto :ffmpeg
)

echo  Downloading portable Python...
curl.exe -fsSL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -o "%EMBED_ZIP%"
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%EMBED_ZIP%'"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
del "%EMBED_ZIP%" >nul 2>&1

:: Enable site-packages
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=Get-ChildItem '%EMBED_DIR%' -Filter '*._pth' | Select -First 1; if($f){$c=Get-Content $f.FullName; $c=$c -replace '#import site','import site'; Set-Content $f.FullName $c}"

echo  [OK] Python ready

:: ── Step 2: FFmpeg (Auto Download) ─────────────────────────────
:ffmpeg
echo.
echo  [2/5] Setting up FFmpeg...

if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg already installed
    goto :pip
)

echo  Downloading FFmpeg (latest build)...
set "FFMPEG_ZIP=%TEMP%\ffmpeg.zip"

curl.exe -fsSL "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "%FFMPEG_ZIP%"
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%FFMPEG_ZIP%'"
)

if not exist "%FFMPEG_ZIP%" (
    echo  [WARN] Could not download FFmpeg. You may need to install it manually later.
    goto :pip
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%TEMP%\ffmpeg_temp' -Force"

:: Move to clean folder
for /d %%d in ("%TEMP%\ffmpeg_temp\ffmpeg*") do xcopy "%%d" "%FFMPEG_DIR%" /E /I /Y >nul
rd /s /q "%TEMP%\ffmpeg_temp" >nul 2>&1
del "%FFMPEG_ZIP%" >nul 2>&1

:: Add FFmpeg to user PATH (for this session + permanent)
set "PATH=%FFMPEG_DIR%\bin;%PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"[Environment]::SetEnvironmentVariable('Path', \"$env:Path;%FFMPEG_DIR%\bin\", [EnvironmentVariableTarget]::User)"

echo  [OK] FFmpeg installed successfully

:: ── Step 3: pip + Dependencies ─────────────────────────────────
:pip
echo.
echo  [3/5] Setting up pip...

if not exist "%EMBED_DIR%\Scripts\pip.exe" (
    curl.exe -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "%GETPIP%"
    "%PYTHON_BIN%" "%GETPIP%" --quiet
    del "%GETPIP%" >nul 2>&1
)

:: ── Step 4: Install Requirements ───────────────────────────────
echo.
echo  [4/5] Installing Python packages...

"%PYTHON_BIN%" -m pip install --upgrade pip
"%PYTHON_BIN%" -m pip install PyQt6 PyQt6-Qt6 PyQt6-Qt6Multimedia yt-dlp

echo  [OK] Core packages installed

:: ── Step 5: Run main installer ─────────────────────────────────
echo.
echo  [5/5] Running main application installer...

if exist "%~dp0install.py" (
    "%PYTHON_BIN%" "%~dp0install.py"
) else (
    echo  Downloading install.py...
    curl.exe -fsSL "https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py" -o "%INSTALL_PY%"
    "%PYTHON_BIN%" "%INSTALL_PY%"
    del "%INSTALL_PY%" >nul 2>&1
)

echo.
echo  ========================================================
echo  Installation completed successfully!
echo  FFmpeg has been automatically installed.
echo  ========================================================
echo.
pause
exit /b 0