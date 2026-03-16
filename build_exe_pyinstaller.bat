@echo off
REM build_pyinstaller.bat - Clean and run PyInstaller for PTTimeline

setlocal

set ROOT=%~dp0
set SPEC=%ROOT%PTTimeline.spec
set BUILD_DIR=%ROOT%build
set OUTPUT_DIR=%ROOT%dist\PTTimeline

echo Cleaning previous build artifacts...
if exist "%BUILD_DIR%"  rmdir /s /q "%BUILD_DIR%"
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
echo   Done.
echo.

echo Running PyInstaller...
echo.
pyinstaller "%SPEC%"

endlocal
