$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$env:JAVA_HOME = Join-Path $projectRoot 'tools\zulu8.96.0.205-ca-jdk8.0.504-win_x64'
$env:Path = "$projectRoot\tools\node-v20.17.0-win-x64;$env:JAVA_HOME\bin;$env:Path"
Push-Location "$projectRoot\upstream\jshERP-boot"
try {
  & "$projectRoot\tools\apache-maven-3.9.9\bin\mvn.cmd" -s "$projectRoot\deployment\maven-settings.xml" "-Dmaven.repo.local=$projectRoot\tools\m2" -B package *> "$projectRoot\evidence\maven-build.log"
  if ($LASTEXITCODE -ne 0) { throw 'Backend build failed; see evidence/maven-build.log' }
} finally { Pop-Location }
Push-Location "$projectRoot\upstream\jshERP-web"
try {
  $env:NODE_OPTIONS = '--openssl-legacy-provider'
  & "$projectRoot\tools\node-v20.17.0-win-x64\npm.cmd" run build *> "$projectRoot\evidence\frontend-build.log"
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed; see evidence/frontend-build.log' }
} finally { Pop-Location }
Write-Output 'Backend and frontend builds completed.'
