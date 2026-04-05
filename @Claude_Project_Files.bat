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

:: Update PTTimeline_Issues.md (markdown) for Claude
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ".\make_issues_markdown.ps1"
copy /y PTTimeline_Issues.md "%target_folder%"

:: Development & Build files
copy /y *.bat "%target_folder%"
copy /y *.ps1 "%target_folder%"
copy /y _*.py "%target_folder%"

:: Support Files
copy /y *.md "%target_folder%"
copy /y *.txt "%target_folder%"

:: Release Notes
copy /y "Releases\*.md" "%target_folder%"

:: Example app INI files (defaults)
copy /y "INI\*.ini" "%target_folder%"

:: Source Files
copy /y requirements.txt "%target_folder%"
copy /y pttedit.py "%target_folder%"
copy /y pttplot.py "%target_folder%"
copy /y pttview.py "%target_folder%"
copy /y "lib\*.py" "%target_folder%"

REM copy /y resources\*.ico "%target_folder%"

copy /y docs\*_UserGuide.html "%target_folder%"

copy /y samples\Test*.* "%target_folder%"
copy /y samples\robotic_pipettor*.* "%target_folder%"

:: Build files
copy /y build_all.bat "%target_folder%"

:: PyInstaller Files
copy /y build_exe.bat "%target_folder%"
copy /y build_exe_pyinstaller.bat "%target_folder%"
copy /y build_exe_folders.bat "%target_folder%"
copy /y PTTimeline.spec "%target_folder%"

:: Inno Setup Files
copy /y build_install.bat "%target_folder%"
copy /y *.VersionInfo "%target_folder%"
copy /y PTTimeline.iss "%target_folder%"
copy /y license.txt "%target_folder%"

:: Cleanup unwanted files
del "%target_folder%"\*.bak*


:: Open the folder
explorer "Claude_Project_Files"