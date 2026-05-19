@echo off
:: ═══════════════════════════════════════════════════════════════
::
::   DIGITALCHURCH DC — Windows Installer Bootstrap
::
::   Double-click this file to install DIGITALCHURCH DC.
::   Does NOT require Python to be pre-installed.
::   Downloads a portable Python silently, uses it once, done.
::
::   Requirements: Windows 10 / 11, internet connection
::
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Self-elevate to Administrator ─────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

:: ── Unblock all files in this folder (Mark of the Web fix) ────
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File -ErrorAction SilentlyContinue"

cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   DIGITALCHURCH DC  —  Windows Installer                 ║
echo  ║   Portrait Split  +  VideoSlicer                         ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  [OK] Running as Administrator
echo.

:: ── Set working dirs ──────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"
set "EMBED_DIR=%INSTALL_DIR%\python-embed"
set "EMBED_PYTHON=%EMBED_DIR%\python.exe"
set "EMBED_ZIP=%TEMP%\dc_python_embed_%RANDOM%.zip"
set "GETPIP=%TEMP%\dc_getpip_%RANDOM%.py"
set "INSTALL_PY=%TEMP%\dc_install_%RANDOM%.py"

:: ── Create install dir ────────────────────────────────────────
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── Step 1: Find or obtain Python ────────────────────────────
echo  [1/4] Locating Python...
echo.

:: Check if our embedded Python is already there from a previous run
if exist "%EMBED_PYTHON%" (
    echo  [OK] Portable Python already present — skipping download
    goto :bootstrap_pip
)

:: Check if a suitable Python is already installed on this machine
set "FOUND_PYTHON="
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%PROGRAMFILES%\Python313\python.exe"
    "%PROGRAMFILES%\Python312\python.exe"
    "%PROGRAMFILES%\Python311\python.exe"
) do (
    if not defined FOUND_PYTHON (
        if exist %%p (
            set "FOUND_PYTHON=%%~p"
        )
    )
)

if defined FOUND_PYTHON (
    echo  [OK] Found installed Python: !FOUND_PYTHON!
    set "EMBED_PYTHON=!FOUND_PYTHON!"
    goto :get_install_script
)

:: No Python found anywhere — download the embeddable package
echo  Python not found on this machine.
echo  Downloading portable Python 3.11 (~12 MB)...
echo  Please wait — this only happens once.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command " ^
    $ProgressPreference = 'SilentlyContinue'; ^
    try { ^
        Invoke-WebRequest ^
            -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' ^
            -OutFile '%EMBED_ZIP%' ^
            -UseBasicParsing; ^
        Write-Host '  [OK] Download complete' ^
    } catch { ^
        Write-Host '  [ERROR] Download failed:' $_.Exception.Message; ^
        exit 1 ^
    } ^
"
if %errorlevel% neq 0 goto :error_download

:: Extract the embeddable zip
echo  Extracting portable Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command " ^
    $ProgressPreference = 'SilentlyContinue'; ^
    Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%EMBED_DIR%' -Force ^
"
if %errorlevel% neq 0 goto :error_extract
del "%EMBED_ZIP%" >nul 2>&1

:: Enable site-packages so pip works (embeddable disables it by default)
powershell -NoProfile -ExecutionPolicy Bypass -Command " ^
    $pth = Get-ChildItem '%EMBED_DIR%' -Filter '*._pth' | Select-Object -First 1; ^
    if ($pth) { ^
        $content = Get-Content $pth.FullName; ^
        $content = $content -replace '#import site','import site'; ^
        Set-Content $pth.FullName $content ^
    } ^
"

echo  [OK] Portable Python 3.11 ready

:: ── Step 2: Bootstrap pip into embedded Python ───────────────
:bootstrap_pip

:: Skip pip bootstrap if pip already exists
if exist "%EMBED_DIR%\Scripts\pip.exe" goto :get_install_script
if exist "%EMBED_DIR%\pip.exe"         goto :get_install_script

:: Only bootstrap pip for our embedded copy (not a system Python)
if /i "!EMBED_PYTHON!" neq "%EMBED_DIR%\python.exe" goto :get_install_script

echo.
echo  [2/4] Bootstrapping pip...

powershell -NoProfile -ExecutionPolicy Bypass -Command " ^
    $ProgressPreference = 'SilentlyContinue'; ^
    Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' ^
        -OutFile '%GETPIP%' -UseBasicParsing ^
"
if not exist "%GETPIP%" goto :error_download

"%EMBED_PYTHON%" "%GETPIP%" --quiet
del "%GETPIP%" >nul 2>&1

if %errorlevel% neq 0 (
    echo  [WARN] pip bootstrap failed — installer may still work
) else (
    echo  [OK] pip ready
)

:: ── Step 3: Get install.py ────────────────────────────────────
:get_install_script
echo.
echo  [3/4] Fetching installer script...

:: Use local copy if available (repo clone or manual download)
if exist "%~dp0install.py" (
    set "INSTALL_PY=%~dp0install.py"
    echo  [OK] Using local install.py
    goto :run
)

powershell -NoProfile -ExecutionPolicy Bypass -Command " ^
    $ProgressPreference = 'SilentlyContinue'; ^
    try { ^
        Invoke-WebRequest ^
            -Uri 'https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py' ^
            -OutFile '%INSTALL_PY%' ^
            -UseBasicParsing; ^
        Write-Host '  [OK] install.py downloaded' ^
    } catch { ^
        Write-Host '  [ERROR]' $_.Exception.Message; ^
        exit 1 ^
    } ^
"
if not exist "%INSTALL_PY%" goto :error_download

:: ── Step 4: Run install.py ────────────────────────────────────
:run
echo.
echo  [4/4] Running DIGITALCHURCH DC installer...
echo.
echo  ──────────────────────────────────────────────────────────
echo.

"%EMBED_PYTHON%" "%INSTALL_PY%"
set "EXIT_CODE=%errorlevel%"

:: Clean up temp install script (keep embedded Python for future use)
if /i "%INSTALL_PY%" neq "%~dp0install.py" (
    del "%INSTALL_PY%" >nul 2>&1
)

if %EXIT_CODE% neq 0 goto :error_installer

:done
echo.
echo  ══════════════════════════════════════════════════════════
echo  All done! You can close this window.
echo  ══════════════════════════════════════════════════════════
echo.
pause
exit /b 0

:: ── Error handlers ────────────────────────────────────────────
:error_download
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ERROR: Could not download a required file.              ║
echo  ║                                                          ║
echo  ║  Check your internet connection and try again.           ║
echo  ║  If behind a proxy, contact your IT administrator.       ║
echo  ║                                                          ║
echo  ║  https://github.com/Dihfahsih1/portrait-split            ║
echo  ╚══════════════════════════════════════════════════════════╝
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
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ERROR: Installation did not complete successfully.      ║
echo  ║  See the output above for details.                       ║
echo  ║                                                          ║
echo  ║  https://github.com/Dihfahsih1/portrait-split            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
exit /b 1
