@echo off
REM build_install.bat - Compile Inno Setup installer for PTTimeline
REM Requires Inno Setup 6 installed at default location.
REM Run after build_exe.bat has produced dist\PTTimeline\

setlocal

set ROOT=%~dp0
set ISS=%ROOT%PTTimeline.iss
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set OUTPUT_DIR=%ROOT%installer

REM Verify PyInstaller output exists before attempting installer build
if not exist "%ROOT%dist\PTTimeline\pttedit.exe" (
    echo ERROR: dist\PTTimeline\pttedit.exe not found.
    echo        Run build.bat first to produce the PyInstaller output.
    echo.
    pause
    exit /b 1
)

REM Verify Inno Setup compiler exists
if not exist %ISCC% (
    echo ERROR: Inno Setup compiler not found at:
    echo        %ISCC%
    echo        Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    echo.
    pause
    exit /b 1
)

REM Create output directory if it doesn't exist
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo.
echo ============================================================
echo  PTTimeline Installer Build
echo ============================================================
echo.

%ISCC% "%ISS%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Inno Setup compilation failed. See output above.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================
echo  INSTALLER BUILD COMPLETE
echo  Output: %OUTPUT_DIR%
echo ============================================================
echo.

endlocal

:: Open the installer folder
explorer "installer"
exit /b 0
