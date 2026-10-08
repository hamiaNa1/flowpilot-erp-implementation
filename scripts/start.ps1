$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& "$projectRoot\.venv\Scripts\python.exe" "$PSScriptRoot\native.py" start
if ($LASTEXITCODE -ne 0) { throw 'Start failed; inspect runtime/logs' }
