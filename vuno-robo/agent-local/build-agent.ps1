param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Assert-LastExitCode {
    param([string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step falhou com codigo $LASTEXITCODE."
    }
}

if (-not (Test-Path ".\.venv")) {
    & $PythonExe -m venv .venv
    Assert-LastExitCode "Criacao do ambiente virtual"
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
Assert-LastExitCode "Atualizacao do pip"
if (Test-Path ".\requirements.txt") {
    & .\.venv\Scripts\python.exe -m pip install -r .\requirements.txt | Out-Null
    Assert-LastExitCode "Instalacao das dependencias do agente"
}

& .\.venv\Scripts\python.exe -m pip install pyinstaller | Out-Null
Assert-LastExitCode "Instalacao do PyInstaller"

$entryPoint = Join-Path $PSScriptRoot "start_agent.py"
$distDir = Join-Path $PSScriptRoot "dist"

& .\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --name vuno-agent `
    --distpath $distDir `
    --onefile `
    $entryPoint
Assert-LastExitCode "Build do executavel do agente"

Write-Host "Build concluido: $distDir\vuno-agent.exe"
Write-Host "Pacote web passara a usar o executavel automaticamente quando este arquivo existir."
Write-Host "Execucao direta: .\dist\vuno-agent.exe --config .\runtime\config.json"
