$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& "$projectRoot\.venv\Scripts\python.exe" "$PSScriptRoot\native.py" stop
if ($LASTEXITCODE -ne 0) { throw 'Stop failed; inspect runtime/logs' }
