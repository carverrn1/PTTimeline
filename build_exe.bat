@echo off
REM build.bat - Master build script for PTTimeline PyInstaller
REM Calls build_pyinstaller.bat then build_folders.bat

setlocal

set ROOT=%~dp0

echo.
echo ============================================================
echo  PTTimeline Build
echo ============================================================
echo.

CALL "%ROOT%build_exe_pyinstaller.bat"
CALL "%ROOT%build_exe_folders.bat"

echo.
echo ============================================================
echo  BUILD COMPLETE
echo  Output: %ROOT%dist\PTTimeline
echo ============================================================
echo.

endlocal
