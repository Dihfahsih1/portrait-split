@echo off
:: ═══════════════════════════════════════════════════════════════
::   DIGITALCHURCH DC — Windows Installer (Stable + Fixed)
::   Properly handles embeddable Python + pip + FFmpeg
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Self-elevate to Administrator ───────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Requesting Administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
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

:: ── Paths ────────────────────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"
set "EMBED_DIR=%INSTALL_DIR%\python-embed"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "PYTHON_BIN=%EMBED_DIR%\python.exe"
set "PTH_FILE=%EMBED_DIR%\python311._pth"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ════════════════════════════════════════════════════════════════
::  STEP 1 — Python Embeddable
:: ════════════════════════════════════════════════════════════════
echo  [1/5] Setting up Python...

if exist "%PYTHON_BIN%" (
    echo  [OK] Portable Python already installed
    goto :check_pth
)

echo  Downloading portable Python 3.11...
curl.exe -fsSL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" ^
    -o "%TEMP%\pyembed.zip"
if %errorlevel% neq 0 (
    echo  [WARN] curl failed, trying PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%TEMP%\pyembed.zip'"
    if !errorlevel! neq 0 (
        echo  [ERROR] Failed to download Python. Check your internet connection.
        pause & exit /b 1
    )
)

echo  Extracting Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%TEMP%\pyembed.zip' -DestinationPath '%EMBED_DIR%' -Force"
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to extract Python archive.
    pause & exit /b 1
)
del "%TEMP%\pyembed.zip" >nul 2>&1

if not exist "%PYTHON_BIN%" (
    echo  [ERROR] Python executable not found after extraction.
    pause & exit /b 1
)
echo  [OK] Python downloaded

:: ── Patch .pth to enable site-packages (required for pip) ───────
:check_pth
if not exist "%PTH_FILE%" (
    echo  [WARN] .pth file not found, skipping site patch
    goto :ffmpeg
)

:: Check if already patched
findstr /C:"import site" "%PTH_FILE%" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Python .pth already patched
    goto :ffmpeg
)

:: Use PowerShell to safely append — avoids trailing-space bug with echo
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Add-Content -Path '%PTH_FILE%' -Value 'import site'"
echo  [OK] Python .pth patched

:: ════════════════════════════════════════════════════════════════
::  STEP 2 — FFmpeg
:: ════════════════════════════════════════════════════════════════
:ffmpeg
echo.
echo  [2/5] Setting up FFmpeg...

if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg already installed
    goto :pip
)

echo  Downloading FFmpeg (this may take a minute)...
curl.exe -fsSL "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" ^
    -o "%TEMP%\ffmpeg.zip"
if %errorlevel% neq 0 (
    echo  [WARN] curl failed, trying PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TEMP%\ffmpeg.zip'"
    if !errorlevel! neq 0 (
        echo  [ERROR] Failed to download FFmpeg. Check your internet connection.
        pause & exit /b 1
    )
)

echo  Extracting FFmpeg...
if exist "%TEMP%\ffmpeg_temp" rd /s /q "%TEMP%\ffmpeg_temp" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%TEMP%\ffmpeg.zip' -DestinationPath '%TEMP%\ffmpeg_temp' -Force"

:: Find the extracted folder (name varies by version) and copy contents
set "FFMPEG_FOUND=0"
for /d %%d in ("%TEMP%\ffmpeg_temp\ffmpeg-*") do (
    if exist "%%d\bin\ffmpeg.exe" (
        echo  Copying FFmpeg from %%d...
        xcopy "%%d\*" "%FFMPEG_DIR%\" /E /I /Y >nul
        set "FFMPEG_FOUND=1"
    )
)

rd /s /q "%TEMP%\ffmpeg_temp" >nul 2>&1
del "%TEMP%\ffmpeg.zip" >nul 2>&1

if "%FFMPEG_FOUND%"=="0" (
    echo  [ERROR] FFmpeg binary not found inside archive. Structure may have changed.
    pause & exit /b 1
)

if not exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo  [ERROR] FFmpeg copy failed. Target path does not contain ffmpeg.exe.
    pause & exit /b 1
)

:: Add FFmpeg to PATH for this session and persistently for the user
set "PATH=%FFMPEG_DIR%\bin;%PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$current = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($current -notlike '*%FFMPEG_DIR%\bin*') { [Environment]::SetEnvironmentVariable('Path', $current + ';%FFMPEG_DIR%\bin', 'User') }"

echo  [OK] FFmpeg installed

:: ════════════════════════════════════════════════════════════════
::  STEP 3 — Bootstrap pip
:: ════════════════════════════════════════════════════════════════
:pip
echo.
echo  [3/5] Bootstrapping pip...

:: Check if pip is already available
"%PYTHON_BIN%" -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] pip already available
    goto :packages
)

echo  Downloading get-pip.py...
curl.exe -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "%TEMP%\get-pip.py"
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to download get-pip.py.
    pause & exit /b 1
)

"%PYTHON_BIN%" "%TEMP%\get-pip.py"
if %errorlevel% neq 0 (
    echo  [ERROR] pip bootstrap failed.
    del "%TEMP%\get-pip.py" >nul 2>&1
    pause & exit /b 1
)
del "%TEMP%\get-pip.py" >nul 2>&1

"%PYTHON_BIN%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] pip installed but not working. Check the .pth patch above.
    pause & exit /b 1
)

echo  [OK] pip ready

:: ════════════════════════════════════════════════════════════════
::  STEP 4 — Install Python Packages
:: ════════════════════════════════════════════════════════════════
:packages
echo.
echo  [4/5] Installing required packages...

echo  Upgrading pip...
"%PYTHON_BIN%" -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo  [WARN] pip upgrade failed, continuing anyway...
)

echo  Installing PyQt6...
"%PYTHON_BIN%" -m pip install PyQt6 PyQt6-Qt6
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install PyQt6.
    pause & exit /b 1
)

echo  Installing yt-dlp...
"%PYTHON_BIN%" -m pip install yt-dlp
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install yt-dlp.
    pause & exit /b 1
)

echo  Installing opencv-python and numpy...
"%PYTHON_BIN%" -m pip install opencv-python numpy
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install opencv-python / numpy.
    pause & exit /b 1
)

echo  [OK] All packages installed

:: ════════════════════════════════════════════════════════════════
::  STEP 5 — Run Main Installer Script
:: ════════════════════════════════════════════════════════════════
echo.
echo  [5/5] Running main installer...

:: Ensure FFmpeg is on PATH for the install.py subprocess
set "PATH=%FFMPEG_DIR%\bin;%PATH%"

if exist "%~dp0install.py" (
    echo  Using local install.py...
    "%PYTHON_BIN%" "%~dp0install.py"
    if !errorlevel! neq 0 (
        echo  [ERROR] install.py exited with an error.
        pause & exit /b 1
    )
) else (
    echo  Downloading install.py from GitHub...
    curl.exe -fsSL "https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py" ^
        -o "%TEMP%\dc_install.py"
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to download install.py from GitHub.
        echo  Make sure the file exists at:
        echo    https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py
        pause & exit /b 1
    )

    :: Sanity check — make sure we didn't download a 404 HTML page
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$content = Get-Content '%TEMP%\dc_install.py' -Raw; if ($content -match '404' -and $content -match 'html') { Write-Host '[ERROR] GitHub returned a 404 page. Check your repository path.'; exit 1 }"
    if %errorlevel% neq 0 (
        del "%TEMP%\dc_install.py" >nul 2>&1
        pause & exit /b 1
    )

    "%PYTHON_BIN%" "%TEMP%\dc_install.py"
    if !errorlevel! neq 0 (
        echo  [ERROR] install.py exited with an error.
        del "%TEMP%\dc_install.py" >nul 2>&1
        pause & exit /b 1
    )
    del "%TEMP%\dc_install.py" >nul 2>&1
)

:: ════════════════════════════════════════════════════════════════
echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|     Installation Completed Successfully!                 ^|
echo  ^|     You can now run VideoSlicer.                         ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.
pause
exit /b 0
