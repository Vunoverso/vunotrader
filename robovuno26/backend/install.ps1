param(
    [string]$PythonExe = "python"
)

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv")) {
    & $PythonExe -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
