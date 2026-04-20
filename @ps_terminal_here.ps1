Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot\set-env.ps1"
Write-Host 'Current Branch:' (git branch --show-current)