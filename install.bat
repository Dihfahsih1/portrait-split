@echo off
:: ═══════════════════════════════════════════════════════════════
::
::   DIGITALCHURCH DC — Windows Installer Bootstrap
::
::   Double-click this file to install DIGITALCHURCH DC.
::   It will install Python if needed, then run install.py.
::
::   Requirements: Windows 10 / 11, internet connection
::
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Pretty header ─────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   DIGITALCHURCH DC  —  Windows Installer                 ║
echo  ║   Portrait Split  +  VideoSlicer                         ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Check Windows version (10+) ───────────────────────────────
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%VERSION%" LSS "10.0" (
    echo  ERROR: Windows 10 or newer is required.
    goto :error
)
echo  [OK] Windows %VERSION% detected

:: ── Check for Python 3.9+ ─────────────────────────────────────
echo  Checking for Python...

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
        echo  [WARN] Python !PYVER! is too old ^(need 3.9+^)
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
    echo  ERROR: winget not available on this system.
    echo.
    echo  Please install Python 3.11 manually:
    echo    https://www.python.org/downloads/
    echo.
    echo  Then run this installer again.
    goto :error
)

winget install --id Python.Python.3.11 ^
    -e ^
    --accept-source-agreements ^
    --accept-package-agreements ^
    --silent

if %errorlevel% neq 0 (
    echo.
    echo  winget install failed. Please install Python 3.11 manually:
    echo    https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during setup.
    goto :error
)

:: Refresh PATH so python is available in this session
call RefreshEnv.cmd >nul 2>&1
:: Fallback: add common Python install paths manually
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"

echo  [OK] Python 3.11 installed

:: ── Run install.py ─────────────────────────────────────────────
:run_installer
echo.
echo  Launching Python installer...
echo.

:: If install.py is next to this .bat, run it directly
if exist "%~dp0install.py" (
    python "%~dp0install.py"
    goto :done
)

:: Otherwise download install.py from the repo
echo  Downloading install.py...
set "INSTALL_PY=%TEMP%\dc_install.py"
set "RAW_URL=https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py"

curl -fsSL "%RAW_URL%" -o "%INSTALL_PY%"
if %errorlevel% neq 0 (
    echo  ERROR: Could not download install.py
    echo  Check your internet connection or visit:
    echo    https://github.com/Dihfahsih1/portrait-split
    goto :error
)

python "%INSTALL_PY%"

:done
echo.
pause
exit /b 0

:error
echo.
echo  ══════════════════════════════════════════════════════════
echo  Installation failed. See error above.
echo  For help visit: https://github.com/Dihfahsih1/portrait-split
echo  ══════════════════════════════════════════════════════════
echo.
pause
exit /b 1
