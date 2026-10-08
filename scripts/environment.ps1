$ErrorActionPreference='Continue'
$projectRoot=Split-Path $PSScriptRoot -Parent
$result=[ordered]@{
  checkedAt=(Get-Date -Format o)
  os=[System.Runtime.InteropServices.RuntimeInformation]::OSDescription
  powershell=$PSVersionTable.PSVersion.ToString()
  source=(git -C "$projectRoot\upstream" remote get-url origin)
  commit=(git -C "$projectRoot\upstream" rev-parse HEAD)
  tag='v3.6'
  dockerInstalled=[bool](Get-Command docker -ErrorAction SilentlyContinue)
  ports=@(Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 3308,6388,9999,8088 | Select-Object LocalAddress,LocalPort)
  diskD=Get-PSDrive D | Select-Object Used,Free
  java=(& "$projectRoot\tools\zulu8.96.0.205-ca-jdk8.0.504-win_x64\bin\java.exe" -version 2>&1 | Out-String).Trim()
  node=(& "$projectRoot\tools\node-v20.17.0-win-x64\node.exe" --version)
  mysql=(& "$projectRoot\tools\mysql-8.0.44-winx64\bin\mysql.exe" --version)
  redis=(& "$projectRoot\tools\redis\redis-server.exe" --version)
  nginx=(& "$projectRoot\tools\nginx-1.28.0\nginx.exe" -v 2>&1 | Out-String).Trim()
}
$result | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 "$projectRoot\evidence\environment.json"
Write-Output "Environment recorded. Docker installed: $($result.dockerInstalled)."
try {
  & "$PSScriptRoot\compose.ps1" check *> "$projectRoot\evidence\compose-execution-attempt.log"
} catch {
  $_.Exception.Message | Add-Content -Encoding utf8 "$projectRoot\evidence\compose-execution-attempt.log"
}
