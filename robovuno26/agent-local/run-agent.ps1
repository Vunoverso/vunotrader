$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe -m app.main --config .\runtime\config.json
if ($LASTEXITCODE -ne 0) {
	exit $LASTEXITCODE
}
