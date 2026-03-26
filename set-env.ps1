# set-env.ps1
#
# Project virtual environment activation script.
#
# CONVENTION:
#   This script assumes the Python virtual environment is in a folder named
#   ".venv" in the same directory as this script. To create the virtual
#   environment for a new project:
#
#     pyenv local x.x.x              # Set the Python version for this folder
#     python -m venv .venv           # Create the virtual environment
#     . .\set-env.ps1                # Activate (first time, before alias is set)
#     pip install <packages>         # Install project dependencies
#     pip freeze > requirements.txt  # Save dependency list
#
# USAGE:
#   If this file was downloaded (e.g. from a browser or Claude), unblock it
#   before first use to avoid PowerShell execution policy errors:
#
#     Unblock-File .\set-env.ps1
#
#   First time in a new PowerShell session, dot-source this script directly:
#
#     . .\set-env.ps1
#
#   For convenience, add the following function to your $PROFILE so that
#   "set-env" works as a command in any project folder containing this script:
#
#     function set-env { . (Join-Path (Get-Location) "set-env.ps1") }
#
#   To edit your $PROFILE:
#
#     notepad $PROFILE
#
#   After adding the function to $PROFILE, you can simply type:
#
#     set-env
#
#   from any project folder that contains a set-env.ps1 file.
#
# EFFECT:
#   - Activates the .venv virtual environment
#   - Sets the PowerShell prompt to: (.venv) <FolderName>>

.\.venv\Scripts\activate
$global:folderName = Split-Path -Leaf (Get-Location)
function global:prompt { "(.venv) $global:folderName> " }
