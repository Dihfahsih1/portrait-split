@echo off
:: ═══════════════════════════════════════════════════════════════
::   DIGITALCHURCH DC — Windows Installer (v5 - with shortcuts)
::   Fixes: window disappearing, silent errors, pth patch, desktop shortcuts
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Installer

:: ── Keep window open on ANY unexpected exit ──────────────────────
if "%~1"=="ELEVATED" goto :main

:: ── Self-elevate to Administrator ───────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Requesting Administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath 'cmd.exe' -ArgumentList '/k \"%~f0\" ELEVATED' -Verb RunAs"
    exit /b 0
)

:: Already admin, run directly
goto :main

:main
cls
echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|     DIGITALCHURCH DC  --  Windows Installer v5          ^|
echo  ^|     Portrait Split  +  Ultra-Fast VideoSlicer           ^|
echo  ^|     Desktop & Start Menu Shortcuts Included             ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.
echo  [OK] Running as Administrator
echo.

:: ── Paths ────────────────────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"
set "EMBED_DIR=%INSTALL_DIR%\python-embed"
set "SCRIPTS_DIR=%EMBED_DIR%\Scripts"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "PYTHON_BIN=%EMBED_DIR%\python.exe"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\DigitalChurch DC"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ════════════════════════════════════════════════════════════════
::  STEP 1 — Python Embeddable
:: ════════════════════════════════════════════════════════════════
echo  [1/5] Setting up Python...

if exist "%PYTHON_BIN%" (
    echo  [OK] Portable Python already installed - skipping download
    goto :patch_pth
)

echo  Downloading portable Python 3.11.9...
curl.exe -fsSL "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" ^
    -o "%TEMP%\pyembed.zip"
if %errorlevel% neq 0 (
    echo  [WARN] curl failed, trying PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%TEMP%\pyembed.zip'"
    if !errorlevel! neq 0 (
        echo.
        echo  [ERROR] Failed to download Python. Check your internet connection.
        echo.
        goto :error
    )
)

echo  Extracting Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%TEMP%\pyembed.zip' -DestinationPath '%EMBED_DIR%' -Force"
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to extract Python archive.
    echo.
    goto :error
)
del "%TEMP%\pyembed.zip" >nul 2>&1

if not exist "%PYTHON_BIN%" (
    echo.
    echo  [ERROR] Python executable not found after extraction.
    echo  Expected: %PYTHON_BIN%
    echo.
    goto :error
)
echo  [OK] Python downloaded and extracted

:: ── Patch .pth to enable site-packages ──────────────────────────
:patch_pth
echo  Patching .pth file to enable site-packages...

:: Find the actual .pth file (name may vary by Python version)
set "PTH_FILE="
for %%f in ("%EMBED_DIR%\python3*._pth") do (
    set "PTH_FILE=%%f"
)

if not defined PTH_FILE (
    echo  [WARN] No ._pth file found - creating python311._pth manually
    set "PTH_FILE=%EMBED_DIR%\python311._pth"
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Set-Content -Path '%EMBED_DIR%\python311._pth' -Value 'python311.zip`n.`n`nimport site'"
    echo  [OK] Created new .pth file
    goto :ffmpeg
)

echo  Found: !PTH_FILE!

:: Use PowerShell to safely replace "#import site" with "import site"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$content = Get-Content '!PTH_FILE!' -Raw; $fixed = $content -replace '#import site','import site'; Set-Content '!PTH_FILE!' -Value $fixed -NoNewline"

:: Verify the patch worked
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$c = Get-Content '!PTH_FILE!' -Raw; if ($c -notmatch '(?m)^import site') { Add-Content '!PTH_FILE!' \"`nimport site\"; Write-Host 'Appended import site' } else { Write-Host 'Patch verified OK' }"

echo  [OK] .pth file patched

:: ════════════════════════════════════════════════════════════════
::  STEP 2 — FFmpeg
:: ════════════════════════════════════════════════════════════════
:ffmpeg
echo.
echo  [2/5] Setting up FFmpeg...

if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg already installed - skipping download
    goto :pip
)

set "FFMPEG_BASE=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
set "FFMPEG_BIN_URL=%FFMPEG_BASE%/ffmpeg-master-latest-win64-gpl.zip"

echo  Downloading FFmpeg (~45MB)...
echo  (Extracting only essential executables)
if not exist "%FFMPEG_DIR%\bin" mkdir "%FFMPEG_DIR%\bin"

curl.exe -fL --progress-bar "%FFMPEG_BIN_URL%" -o "%TEMP%\ffmpeg.zip"
if %errorlevel% neq 0 (
    echo  [WARN] curl failed, trying PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_BIN_URL%' -OutFile '%TEMP%\ffmpeg.zip'"
    if !errorlevel! neq 0 (
        echo.
        echo  [ERROR] Failed to download FFmpeg.
        echo  Try manually downloading from: %FFMPEG_BIN_URL%
        echo.
        goto :error
    )
)

echo  Extracting FFmpeg (ffmpeg.exe, ffprobe.exe, ffplay.exe only)...
if exist "%TEMP%\ffmpeg_temp" rd /s /q "%TEMP%\ffmpeg_temp" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Add-Type -Assembly 'System.IO.Compression.FileSystem'; $z=[IO.Compression.ZipFile]::OpenRead('%TEMP%\ffmpeg.zip'); foreach($e in $z.Entries){ if($e.Name -match '^(ffmpeg|ffprobe|ffplay)\.exe$'){ [IO.Compression.ZipFileExtensions]::ExtractToFile($e,'%FFMPEG_DIR%\bin\'+$e.Name,$true) } }; $z.Dispose()"

del "%TEMP%\ffmpeg.zip" >nul 2>&1

if not exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo.
    echo  [ERROR] FFmpeg extraction failed - ffmpeg.exe not found.
    echo.
    goto :error
)

:: Add FFmpeg to PATH for this session and permanently for the user
set "PATH=%FFMPEG_DIR%\bin;%PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$cur=[Environment]::GetEnvironmentVariable('Path','User'); if ($cur -notlike '*%FFMPEG_DIR%*') { [Environment]::SetEnvironmentVariable('Path',$cur+';%FFMPEG_DIR%\bin','User') }"

echo  [OK] FFmpeg installed and added to PATH

:: ════════════════════════════════════════════════════════════════
::  STEP 3 — Bootstrap pip
:: ════════════════════════════════════════════════════════════════
:pip
echo.
echo  [3/5] Bootstrapping pip...

set "PATH=%SCRIPTS_DIR%;%FFMPEG_DIR%\bin;%PATH%"

"%PYTHON_BIN%" -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] pip already available
    goto :packages
)

echo  Downloading get-pip.py...
curl.exe -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "%TEMP%\get-pip.py"
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to download get-pip.py.
    echo.
    goto :error
)

echo  Installing pip...
"%PYTHON_BIN%" "%TEMP%\get-pip.py" --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] pip bootstrap failed.
    echo.
    echo  Most likely cause: the .pth file was not patched correctly.
    echo  Check this file - it must contain "import site" (no # prefix):
    echo    !PTH_FILE!
    echo.
    del "%TEMP%\get-pip.py" >nul 2>&1
    goto :error
)
del "%TEMP%\get-pip.py" >nul 2>&1

"%PYTHON_BIN%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] pip still not working after install.
    echo  Manual fix: open this file and ensure "import site" appears
    echo  on its own line with NO # prefix:
    echo    !PTH_FILE!
    echo.
    goto :error
)
echo  [OK] pip ready

:: ════════════════════════════════════════════════════════════════
::  STEP 4 — Install Python Packages
:: ════════════════════════════════════════════════════════════════
:packages
echo.
echo  [4/5] Installing required packages...

echo  Upgrading pip...
"%PYTHON_BIN%" -m pip install --upgrade pip --quiet --no-warn-script-location
if %errorlevel% neq 0 echo  [WARN] pip upgrade failed, continuing...

echo  Installing PyQt6 (GUI framework)...
"%PYTHON_BIN%" -m pip install PyQt6 PyQt6-Qt6 --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install PyQt6.
    echo.
    goto :error
)

echo  Installing yt-dlp (video downloader)...
"%PYTHON_BIN%" -m pip install yt-dlp --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install yt-dlp.
    echo.
    goto :error
)

echo  Installing opencv-python and numpy (video processing)...
"%PYTHON_BIN%" -m pip install opencv-python numpy --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install opencv-python / numpy.
    echo.
    goto :error
)

echo  Installing pywin32 (for shortcut creation)...
"%PYTHON_BIN%" -m pip install pywin32 winshell --no-warn-script-location
if %errorlevel% neq 0 (
    echo  [WARN] pywin32 install failed - shortcuts will use PowerShell fallback
)

echo  [OK] All packages installed

:: ════════════════════════════════════════════════════════════════
::  STEP 5 — Run Main Installer Script
:: ════════════════════════════════════════════════════════════════
echo.
echo  [5/5] Running main installer...

set "PATH=%FFMPEG_DIR%\bin;%SCRIPTS_DIR%;%PATH%"

if exist "%~dp0install.py" (
    echo  Using local install.py...
    "%PYTHON_BIN%" "%~dp0install.py"
    if !errorlevel! neq 0 (
        echo.
        echo  [ERROR] install.py exited with an error.
        echo.
        goto :error
    )
) else (
    echo  Downloading install.py from GitHub...
    curl.exe -fsSL "https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.py" ^
        -o "%TEMP%\dc_install.py"
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] Failed to download install.py from GitHub.
        echo  Check that the file exists at:
        echo    https://github.com/Dihfahsih1/portrait-split/blob/main/install.py
        echo.
        goto :error
    )

    :: Check for 404 HTML response
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$c=Get-Content '%TEMP%\dc_install.py' -Raw; if ($c -match '404' -and $c -match '<html') { Write-Host '[ERROR] GitHub returned a 404 page - file not found in repo'; exit 1 }"
    if %errorlevel% neq 0 (
        del "%TEMP%\dc_install.py" >nul 2>&1
        goto :error
    )

    "%PYTHON_BIN%" "%TEMP%\dc_install.py"
    if !errorlevel! neq 0 (
        echo.
        echo  [ERROR] install.py exited with an error.
        echo.
        del "%TEMP%\dc_install.py" >nul 2>&1
        goto :error
    )
    del "%TEMP%\dc_install.py" >nul 2>&1
)

:: ════════════════════════════════════════════════════════════════
::  CREATE SHORTCUTS - Additional verification
:: ════════════════════════════════════════════════════════════════
echo.
echo  Creating Desktop and Start Menu shortcuts...

:: Create Start Menu folder
if not exist "%START_MENU_DIR%" mkdir "%START_MENU_DIR%"

:: Function to create shortcut using PowerShell
call :CreateShortcut "DigitalChurch DC Suite" "digitalchurch_dc.py" "DigitalChurch DC Media Suite - Complete toolkit"
call :CreateShortcut "Portrait Split GUI" "portrait_split_gui.py" "Quick portrait video splitter with GUI"
call :CreateShortcut "VideoSlicer Ultra Fast" "video_slicer.py" "Ultra-fast video slicer with frame-accurate cutting"

:: Create uninstall shortcut in Start Menu
if exist "%INSTALL_DIR%\uninstall.bat" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU_DIR%\Uninstall DigitalChurch DC.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\uninstall.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Uninstall DigitalChurch DC Media Suite'; $Shortcut.Save()"
    echo  [OK] Start Menu: Uninstall shortcut created
)

echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|     Installation Completed Successfully!                 ^|
echo  ^|                                                          ^|
echo  ^|     Desktop Shortcuts Created:                           ^|
echo  ^|       • DigitalChurch DC Suite                           ^|
echo  ^|       • Portrait Split GUI                               ^|
echo  ^|       • VideoSlicer Ultra Fast                           ^|
echo  ^|                                                          ^|
echo  ^|     Start Menu Folder:                                   ^|
echo  ^|       DigitalChurch DC (All apps + Uninstaller)          ^|
echo  ^|                                                          ^|
echo  ^|     Quick Launch:                                        ^|
echo  ^|       Double-click any desktop shortcut                  ^|
echo  ^|       or find in Start Menu                              ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.
echo  Press any key to close this window...
pause >nul
exit /b 0

:: ════════════════════════════════════════════════════════════════
::  SHORTCUT CREATION SUBROUTINE
:: ════════════════════════════════════════════════════════════════
:CreateShortcut
set "SHORTCUT_NAME=%~1"
set "SCRIPT_NAME=%~2"
set "DESCRIPTION=%~3"

if not exist "%INSTALL_DIR%\%SCRIPT_NAME%" (
    echo  [WARN] Script not found: %SCRIPT_NAME% - skipping shortcut
    goto :eof
)

:: Create Desktop shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk'); $Shortcut.TargetPath = '%PYTHON_BIN%'; $Shortcut.Arguments = '\"%INSTALL_DIR%\%SCRIPT_NAME%\"'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = '%DESCRIPTION%'; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo  [OK] Desktop shortcut created: %SHORTCUT_NAME%
) else (
    echo  [WARN] Failed to create Desktop shortcut: %SHORTCUT_NAME%
)

:: Create Start Menu shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU_DIR%\%SHORTCUT_NAME%.lnk'); $Shortcut.TargetPath = '%PYTHON_BIN%'; $Shortcut.Arguments = '\"%INSTALL_DIR%\%SCRIPT_NAME%\"'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = '%DESCRIPTION%'; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo  [OK] Start Menu shortcut created: %SHORTCUT_NAME%
) else (
    echo  [WARN] Failed to create Start Menu shortcut: %SHORTCUT_NAME%
)
goto :eof

:: ════════════════════════════════════════════════════════════════
::  ERROR HANDLER — always shows the error before pausing
:: ════════════════════════════════════════════════════════════════
:error
echo.
echo  ============================================================
echo   INSTALLATION FAILED
echo   Scroll up to find the [ERROR] message above.
echo   Screenshot this window and share it for support.
echo  ============================================================
echo.
echo  Troubleshooting tips:
echo   1. Check your internet connection
echo   2. Disable antivirus temporarily
echo   3. Run as Administrator
echo   4. Check GitHub repository is accessible
echo.
echo  Manual installation:
echo   1. Install Python 3.11 from python.org
echo   2. Install FFmpeg from gyan.dev
echo   3. Run: pip install PyQt6 opencv-python numpy yt-dlp pywin32
echo.
echo  Press any key to close...
pause >nul
exit /b 1