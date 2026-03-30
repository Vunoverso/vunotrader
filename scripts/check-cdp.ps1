try {
  $list = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:9222/json/list"
  Write-Output "CDP_LIST_OK"
  Write-Output $list.Content
} catch {
  Write-Error "CDP indisponivel em 127.0.0.1:9222"
  exit 1
}
