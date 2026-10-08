$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
New-Item -ItemType Directory -Force tools,evidence | Out-Null
$resources=@(
  @{Name='jdk8'; Url='https://cdn.azul.com/zulu/bin/zulu8.96.0.205-ca-jdk8.0.504-win_x64.zip'; Folder='zulu8.96.0.205-ca-jdk8.0.504-win_x64'; Target='tools'},
  @{Name='maven'; Url='https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.zip'; Folder='apache-maven-3.9.9'; Target='tools'},
  @{Name='mysql'; Url='https://cdn.mysql.com/Downloads/MySQL-8.0/mysql-8.0.44-winx64.zip'; Folder='mysql-8.0.44-winx64'; Target='tools'},
  @{Name='redis'; Url='https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip'; Folder='redis'; Target='tools/redis'},
  @{Name='nginx'; Url='https://nginx.org/download/nginx-1.28.0.zip'; Folder='nginx-1.28.0'; Target='tools'},
  @{Name='node'; Url='https://nodejs.org/dist/v20.17.0/node-v20.17.0-win-x64.zip'; Folder='node-v20.17.0-win-x64'; Target='tools'}
)
foreach ($resource in $resources) {
  if (-not (Test-Path "tools/$($resource.Folder)")) {
    $archive="tools/$($resource.Name).zip"
    if (-not (Test-Path $archive)) {
      curl.exe -fL --retry 2 --max-time 300 $resource.Url -o $archive
      if ($LASTEXITCODE -ne 0) { throw "Download failed: $($resource.Name)" }
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $resource.Target
  }
}
if (-not (Test-Path upstream)) {
  git clone --depth 1 --branch v3.6 https://github.com/jishenghua/jshERP.git upstream
  if ($LASTEXITCODE -ne 0) { throw 'Source clone failed' }
}
$actualCommit=(git -C upstream rev-parse HEAD).Trim()
if ($actualCommit -ne '8f28e7c2fe54d54de3621a414f5df1833dc5a55f') { throw 'Source commit mismatch' }
git -C upstream apply --check "$projectRoot/deployment/windows-export.patch" 2>$null
if ($LASTEXITCODE -eq 0) {
  git -C upstream apply "$projectRoot/deployment/windows-export.patch"
} else {
  git -C upstream apply --reverse --check "$projectRoot/deployment/windows-export.patch" 2>$null
  if ($LASTEXITCODE -ne 0) { throw 'Source differs from reviewed compatibility patch' }
}
if (-not (Test-Path .venv)) { python -m venv .venv }
& .venv/Scripts/python.exe -m pip install --cache-dir tools/pip-cache -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed' }
Copy-Item deployment/package-lock.json upstream/jshERP-web/package-lock.json -Force
$env:Path="$projectRoot/tools/node-v20.17.0-win-x64;$env:Path"
Push-Location upstream/jshERP-web
try {
  & "$projectRoot/tools/node-v20.17.0-win-x64/npm.cmd" ci --legacy-peer-deps --cache "$projectRoot/tools/npm-cache" --registry https://registry.npmjs.org
  if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed' }
} finally { Pop-Location }
& "$PSScriptRoot/build.ps1"
if (-not (Test-Path runtime/mysql/auto.cnf)) {
  & .venv/Scripts/python.exe scripts/native.py init
  if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed' }
}
& "$PSScriptRoot/start.ps1"
Write-Output 'Setup completed. Run migrate.py templates, validate, import to configure demo business.'
