@echo on
REM build_all.bat - Master build script for PTTimeline

setlocal EnableExtensions EnableDelayedExpansion


set ROOT=%~dp0

@echo.
@echo ============================================================
@echo  PTTimeline Build All (PyInstaller and Inno Setup)
@echo ============================================================
@echo.

set "StartPyInstaller=%TIME%"
CALL "%ROOT%build_exe.bat" >%ROOT%build_exe.out 2>&1
set "StartInnoSetup=%TIME%"
CALL "%ROOT%build_install.bat" >%ROOT%build_install.out 2>&1
set "CompletedAll=%TIME%"

@echo.
@echo ============================================================
@echo  BUILD ALL COMPLETE
@echo  StartPyInstaller : %StartPyInstaller%
@echo  StartInnoSetup   : %StartInnoSetup%
@echo  CompletedAll     : %CompletedAll%
@echo ============================================================
@echo.

endlocal
