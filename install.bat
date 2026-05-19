@echo off
:: ═══════════════════════════════════════════════════════════════
::
::   DIGITALCHURCH DC — Windows Installer Bootstrap
::
::   Double-click this file to install DIGITALCHURCH DC.
::   It will request admin rights, install Python if needed,
::   then run install.py.
::
::   Requirements: Windows 10 / 11, internet connection
::
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Self-elevate to Administrator ─────────────────────────────
:: Check if we already have admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Requesting administrator privileges...
    echo  ^(A UAC prompt will appear — click Yes to continue^)
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

:: ── Unblock this script and siblings (Mark of the Web fix) ────
:: Windows blocks files downloaded from the internet — this removes that flag
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue"

:: ── Pretty header ─────────────────────────────────────────────
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   DIGITALCHURCH DC  —  Windows Installer                 ║
echo  ║   Portrait Split  +  VideoSlicer                         ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Running as Administrator: OK
echo.

:: ── Check Windows version (10+) ───────────────────────────────
for /f "tokens=4-5 delims=. " %%i in ('ver') do set WIN_VER=%%i.%%j
echo  [OK] Windows %WIN_VER% detected

:: ── Ensure TLS 1.2 is enabled for downloads ───────────────────
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12" ^
    >nul 2>&1

:: ── Check for Python 3.9+ ─────────────────────────────────────
echo  Checking for Python...

:: Refresh PATH to catch any recently installed Python
for /f "delims=" %%i in ('powershell -NoProfile -Command ^
    "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') ^
    do set "PATH=%%i"

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
    for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
        set PYMAJ=%%a
        set PYMIN=%%b
    )
    if !PYMAJ! GEQ 3 if !PYMIN! GEQ 9 (
        echo  [OK] Python !PYVER! found
        goto :run_installer
    ) else (
        echo  [WARN] Python !PYVER! is too old ^(need 3.9+^) — installing newer version...
        goto :install_python
    )
) else (
    echo  [INFO] Python not found — installing via winget...
    goto :install_python
)

:: ── Install Python via winget ──────────────────────────────────
:install_python
echo.
echo  Installing Python 3.11 via winget...
echo  ^(This may take a minute — please wait^)
echo.

winget --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  winget not available — trying direct download...
    goto :install_python_direct
)

winget install --id Python.Python.3.11 ^
    -e ^
    --accept-source-agreements ^
    --accept-package-agreements ^
    --silent

if %errorlevel% neq 0 (
    echo  winget install failed — trying direct download...
    goto :install_python_direct
)
goto :python_installed

:install_python_direct
:: Download Python installer directly as a fallback
echo  Downloading Python 3.11 installer...
set "PY_INSTALLER=%TEMP%\python311_installer.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Could not download Python. Please install manually:
    echo    https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during setup.
    goto :error
)
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo  ERROR: Python installer failed. Please install manually:
    echo    https://www.python.org/downloads/
    goto :error
)

:python_installed
:: Refresh PATH so python is visible in this session
for /f "delims=" %%i in ('powershell -NoProfile -Command ^
    "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') ^
    do set "PATH=%%i"

:: Also add common install paths as a safety net
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
set "PATH=%PATH%;%PROGRAMFILES%\Python311;%PROGRAMFILES%\Python311\Scripts"

echo  [OK] Python 3.11 installed

:: ── Run install.py ─────────────────────────────────────────────
:run_installer
echo.
echo  Launching Python installer...
echo.

:: If install.py is sitting next to this .bat, use it directly
if exist "%~dp0install.py" (
    python "%~dp0install.py"
    goto :done
)

:: Otherwise download install.py from the repo
echo  Downloading install.py from GitHub...
set "INSTALL_PY=%TEMP%\dc_install_%RANDOM%.py"
set "RAW_URL=https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py"

:: Try curl first (built into Windows 10/11)
curl -fsSL "%RAW_URL%" -o "%INSTALL_PY%" >nul 2>&1

:: Fall back to PowerShell if curl failed
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Invoke-WebRequest -Uri '%RAW_URL%' -OutFile '%INSTALL_PY%' -UseBasicParsing"
)

if not exist "%INSTALL_PY%" (
    echo.
    echo  ERROR: Could not download install.py
    echo  Check your internet connection or visit:
    echo    https://github.com/Dihfahsih1/portrait-split
    goto :error
)

python "%INSTALL_PY%"

:done
echo.
echo  Press any key to close this window...
pause >nul
exit /b 0

:error
echo.
echo  ══════════════════════════════════════════════════════════
echo  Installation failed. See the error message above.
echo  For help visit: https://github.com/Dihfahsih1/portrait-split
echo  ══════════════════════════════════════════════════════════
echo.
pause
exit /b 1
