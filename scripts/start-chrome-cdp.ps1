$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $chromePath)) {
  Write-Error "Chrome nao encontrado no caminho padrao."
  exit 1
}

$profileDir = "E:\robotrademeta5\.chrome-cdp-profile"
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

Start-Process $chromePath "--remote-debugging-port=9222 --user-data-dir=\"$profileDir\" http://localhost:3000/#top"
Start-Sleep -Seconds 2

try {
  $cdpResponse = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:9222/json/version"
  Write-Output "CDP_ATIVO_CHROME"
  Write-Output $cdpResponse.Content
} catch {
  Write-Error "Falha ao validar endpoint CDP em 9222."
  exit 1
}
