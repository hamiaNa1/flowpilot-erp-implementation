param([ValidateSet('start','stop','restart','status','logs','check')][string]$Action='start')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed. Use scripts/start.ps1 for the verified Windows deployment.' }
Push-Location $projectRoot
try {
  switch ($Action) {
    start { docker compose up -d --build --wait }
    stop { docker compose stop }
    restart { docker compose restart }
    status { docker compose ps }
    logs { docker compose logs --tail 100 }
    check { docker compose config --quiet }
  }
  if ($LASTEXITCODE -ne 0) { throw 'Docker Compose command failed' }
} finally { Pop-Location }
