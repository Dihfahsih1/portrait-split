@echo off
:: ═══════════════════════════════════════════════════════════════
::
::   DIGITALCHURCH DC — Windows Installer Bootstrap
::
::   Double-click this file to install DIGITALCHURCH DC.
::   Does NOT require Python to be pre-installed.
::
::   Requirements: Windows 10 / 11, internet connection
::
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Self-elevate to Administrator ─────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

:: ── Unblock downloaded files (Mark of the Web fix) ────────────
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue"

cls
echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|   DIGITALCHURCH DC  --  Windows Installer               ^|
echo  ^|   Portrait Split  +  VideoSlicer                        ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.
echo  [OK] Running as Administrator
echo.

:: ── Paths ─────────────────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"
set "EMBED_DIR=%INSTALL_DIR%\python-embed"
set "EMBED_PYTHON=%EMBED_DIR%\python.exe"
set "EMBED_ZIP=%TEMP%\dc_python_%RANDOM%.zip"
set "GETPIP=%TEMP%\dc_getpip_%RANDOM%.py"
set "INSTALL_PY=%TEMP%\dc_install_%RANDOM%.py"
set "PYTHON_BIN="

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── Step 1: Locate Python ─────────────────────────────────────
echo  [1/4] Locating Python...

:: Reuse our own embedded Python from a previous run
if exist "%EMBED_PYTHON%" (
    set "PYTHON_BIN=%EMBED_PYTHON%"
    echo  [OK] Portable Python already present
    goto :get_install_script
)

:: Scan common install locations (bypasses PATH issues entirely)
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%PROGRAMFILES%\Python313\python.exe"
    "%PROGRAMFILES%\Python312\python.exe"
    "%PROGRAMFILES%\Python311\python.exe"
    "%PROGRAMFILES%\Python310\python.exe"
) do (
    if not defined PYTHON_BIN (
        if exist %%p (
            set "PYTHON_BIN=%%~p"
            echo  [OK] Found Python: %%~p
        )
    )
)

if defined PYTHON_BIN goto :get_install_script

:: ── Download embeddable Python (no install needed) ────────────
echo  Python not found -- downloading portable Python 3.11...
echo  Please wait, this only happens once (~12 MB).
echo.

curl.exe -fsSL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -o "%EMBED_ZIP%"
if %errorlevel% neq 0 (
    echo  [ERROR] curl failed. Trying PowerShell fallback...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='SilentlyContinue';$ProgressPreference=$p;Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%EMBED_ZIP%' -UseBasicParsing"
)
if not exist "%EMBED_ZIP%" goto :error_download
echo  [OK] Downloaded

:: Extract
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
if %errorlevel% neq 0 goto :error_extract
del "%EMBED_ZIP%" >nul 2>&1

:: Enable site-packages (embeddable Python disables it by default)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=Get-ChildItem '%EMBED_DIR%' -Filter '*._pth'|Select -First 1;if($f){$c=Get-Content $f.FullName;$c=$c -replace '#import site','import site';Set-Content $f.FullName $c}"

set "PYTHON_BIN=%EMBED_PYTHON%"
echo  [OK] Portable Python 3.11 ready

:: ── Step 2: Bootstrap pip (only for our embedded Python) ──────
echo.
echo  [2/4] Bootstrapping pip...

if exist "%EMBED_DIR%\Scripts\pip.exe" goto :get_install_script

curl.exe -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "%GETPIP%"
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%' -UseBasicParsing"
)
if not exist "%GETPIP%" (
    echo  [WARN] Could not get pip -- continuing anyway
    goto :get_install_script
)

"%PYTHON_BIN%" "%GETPIP%" --quiet
del "%GETPIP%" >nul 2>&1
echo  [OK] pip ready

:: ── Step 3: Get install.py ────────────────────────────────────
:get_install_script
echo.
echo  [3/4] Fetching installer script...

:: Use local copy if sitting next to this .bat
if exist "%~dp0install.py" (
    set "INSTALL_PY=%~dp0install.py"
    echo  [OK] Using local install.py
    goto :run
)

set "RAW_URL=https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py"

curl.exe -fsSL "%RAW_URL%" -o "%INSTALL_PY%"
if %errorlevel% neq 0 (
    echo  [INFO] curl failed, trying PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri '%RAW_URL%' -OutFile '%INSTALL_PY%' -UseBasicParsing"
)
if not exist "%INSTALL_PY%" goto :error_download
echo  [OK] install.py downloaded

:: ── Step 4: Run install.py ────────────────────────────────────
:run
echo.
echo  [4/4] Running DIGITALCHURCH DC installer...
echo.
echo  ----------------------------------------------------------
echo.

"%PYTHON_BIN%" "%INSTALL_PY%"
set "EXIT_CODE=%errorlevel%"

if /i "%INSTALL_PY%" neq "%~dp0install.py" del "%INSTALL_PY%" >nul 2>&1
if %EXIT_CODE% neq 0 goto :error_installer

:done
echo.
echo  All done! You can close this window.
echo.
pause
exit /b 0

:: ── Errors ────────────────────────────────────────────────────
:error_download
echo.
echo  +----------------------------------------------------------+
echo  ^|  ERROR: Could not download a required file.             ^|
echo  ^|  Check your internet connection and try again.          ^|
echo  ^|  https://github.com/Dihfahsih1/portrait-split           ^|
echo  +----------------------------------------------------------+
echo.
pause
exit /b 1

:error_extract
echo.
echo  ERROR: Could not extract Python package.
echo  Make sure %INSTALL_DIR% is writable and try again.
echo.
pause
exit /b 1

:error_installer
echo.
echo  +----------------------------------------------------------+
echo  ^|  ERROR: Installation did not complete.                  ^|
echo  ^|  See the output above for details.                      ^|
echo  ^|  https://github.com/Dihfahsih1/portrait-split           ^|
echo  +----------------------------------------------------------+
echo.
pause
exit /b 1
