@echo off
REM Project_Files.bat - Creates an updated Project_Files folder with all the files for this
REM project in a flat format (no folders) since Claude Chat Projects can't handle folders

setlocal

set ROOT=%~dp0

set "target_folder=Claude_Project_Files"

:: 1. Check if the folder exists
if exist "%target_folder%" (
    echo Deleting existing folder: %target_folder%
    
    :: 2. Remove directory and all subdirectories/files quietly
    rmdir /s /q "%target_folder%"
)

:: 3. Recreate the folder
echo Creating fresh folder: %target_folder%
mkdir "%target_folder%"

:: Support Files
copy Claude_Project_Files.bat "%target_folder%"
copy DECISIONS.md "%target_folder%"
copy PTTimeline_Program_Files_Layout.txt "%target_folder%"

:: Source Files
copy requirements.txt "%target_folder%"
copy pttedit.py "%target_folder%"
copy pttplot.py "%target_folder%"
copy pttview.py "%target_folder%"
copy "lib\pttedit_delegates.py" "%target_folder%"
copy "lib\pttedit_expression_evaluator.py" "%target_folder%"
copy "lib\ptt_config.py" "%target_folder%"
copy "lib\ptt_appinfo.py" "%target_folder%"
copy "lib\ptt_debugging.py" "%target_folder%"
copy "lib\ptt_splash.py" "%target_folder%"

REM copy resources\*.ico "%target_folder%"

copy docs\*_UserGuide.html "%target_folder%"

copy samples\Test*.* "%target_folder%"
copy samples\robotic_pipettor*.* "%target_folder%"

:: Build files
copy build_all.bat "%target_folder%"

:: PyInstaller Files
copy build_exe.bat "%target_folder%"
copy build_exe_pyinstaller.bat "%target_folder%"
copy build_exe_folders.bat "%target_folder%"
copy PTTimeline.spec "%target_folder%"

:: Inno Setup Files
copy build_install.bat "%target_folder%"
copy *.VersionInfo "%target_folder%"
copy PTTimeline.iss "%target_folder%"
copy license.txt "%target_folder%"
