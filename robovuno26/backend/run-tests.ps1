Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Python do backend nao encontrado. Rode .\install.ps1 antes."
    exit 1
}

& .\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& .\.venv\Scripts\python.exe -m compileall -f .\app .\tools
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& .\.venv\Scripts\python.exe -m pytest
exit $LASTEXITCODE
