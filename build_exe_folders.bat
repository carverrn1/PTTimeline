@echo off
REM build_folders.bat - Copy runtime folders into dist\PTTimeline alongside EXEs

setlocal

set ROOT=%~dp0
set OUTPUT_DIR=%ROOT%dist\PTTimeline

echo Copying runtime folders...
REM xcopy /e /i /y /q "%ROOT%resources" "%OUTPUT_DIR%\resources\"
rmdir /s /q "%OUTPUT_DIR%\resources\"
mkdir "%OUTPUT_DIR%\resources\"
copy "%ROOT%resources\*.ico" "%OUTPUT_DIR%\resources\"
copy "%ROOT%resources\*.png" "%OUTPUT_DIR%\resources\"
echo   Copied: resources\
REM xcopy /e /i /y /q "%ROOT%samples"   "%OUTPUT_DIR%\samples\"
rmdir /s /q "%OUTPUT_DIR%\samples\"
mkdir "%OUTPUT_DIR%\samples\"
copy "%ROOT%samples\*.pttd" "%OUTPUT_DIR%\samples\"
copy "%ROOT%samples\*.pttp" "%OUTPUT_DIR%\samples\"
echo   Copied: samples\
REM xcopy /e /i /y /q "%ROOT%docs"      "%OUTPUT_DIR%\docs\"
rmdir /s /q "%OUTPUT_DIR%\docs\"
mkdir "%OUTPUT_DIR%\docs\"
copy "%ROOT%docs\*.html" "%OUTPUT_DIR%\docs\"
echo   Copied: docs\

endlocal
