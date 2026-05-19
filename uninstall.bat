@echo off
:: ═══════════════════════════════════════════════════════════════
::   DIGITALCHURCH DC — Uninstaller
::   Removes Python, FFmpeg, all apps and shortcuts
:: ═══════════════════════════════════════════════════════════════
setlocal EnableDelayedExpansion

title DIGITALCHURCH DC — Uninstaller

echo.
echo  +----------------------------------------------------------+
echo  ^|                                                          ^|
echo  ^|     DIGITALCHURCH DC  —  Uninstaller                    ^|
echo  ^|     This will remove ALL installed components           ^|
echo  ^|                                                          ^|
echo  +----------------------------------------------------------+
echo.

:: Self-elevate to Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

set "INSTALL_DIR=%LOCALAPPDATA%\DigitalChurch"

echo WARNING: This will permanently delete:
echo.
echo    • %INSTALL_DIR%
echo    • All DigitalChurch shortcuts in Start Menu
echo    • FFmpeg and Python portable installation
echo.

choice /C YN /M "Are you sure you want to uninstall DIGITALCHURCH DC?"
if %errorlevel% == 2 (
    echo.
    echo Uninstallation cancelled by user.
    pause
    exit /b 0
)

echo.
echo Removing DIGITALCHURCH DC...

:: Remove main installation folder
if exist "%INSTALL_DIR%" (
    rd /s /q "%INSTALL_DIR%" >nul 2>&1
    echo [OK] Removed main installation folder
) else (
    echo [INFO] Installation folder not found
)

:: Remove Start Menu shortcuts
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\DigitalChurch DC"
if exist "%START_MENU%" (
    rd /s /q "%START_MENU%" >nul 2>&1
    echo [OK] Removed Start Menu folder
)

:: Remove individual shortcuts if they exist
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DIGITALCHURCH DC.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Portrait Split.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\VideoSlicer.lnk" 2>nul

echo.
echo ========================================================
echo Uninstallation Completed Successfully!
echo All files and shortcuts have been removed.
echo ========================================================
echo.
pause
exit /b 0