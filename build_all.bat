@echo on
REM build_all.bat - Master build script for PTTimeline
setlocal EnableExtensions EnableDelayedExpansion
set ROOT=%~dp0
python _ptt_update_version.py || goto :error
@echo.
@echo ============================================================
@echo  PTTimeline Build All (PyInstaller and Inno Setup)
@echo ============================================================
@echo.
set "StartPyInstaller=%TIME%"
CALL "%ROOT%build_exe.bat" >%ROOT%build_exe.out 2>&1 || goto :error
set "StartInnoSetup=%TIME%"
CALL "%ROOT%build_install.bat" >%ROOT%build_install.out 2>&1 || goto :error
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
goto :eof

:error
echo.
echo ERROR: Build aborted.
endlocal
exit /b 1