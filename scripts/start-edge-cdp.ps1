$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgePath)) {
  $edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
}

if (-not (Test-Path $edgePath)) {
  Write-Error "Edge nao encontrado nos caminhos padrao."
  exit 1
}

$profileDir = "E:\robotrademeta5\.edge-cdp-profile"
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

$edgeArgs = @(
  "--remote-debugging-port=9222",
  "--user-data-dir=$profileDir",
  "http://localhost:3000/#top"
)

Start-Process -FilePath $edgePath -ArgumentList $edgeArgs
Start-Sleep -Seconds 2

try {
  $version = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:9222/json/version"
  Write-Output "CDP_ATIVO"
  Write-Output $version.Content
} catch {
  Write-Error "Falha ao validar endpoint CDP em 9222."
  exit 1
}
