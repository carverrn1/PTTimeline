Start-Process pwsh.exe `
  -WorkingDirectory $PSScriptRoot `
  -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-Command', "& { Set-Location -LiteralPath '$PSScriptRoot'; . '$PSScriptRoot\set-env.ps1'; Write-Host 'Current Branch:' (git branch --show-current) }"
  )