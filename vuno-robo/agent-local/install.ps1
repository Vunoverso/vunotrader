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

New-Item -ItemType Directory -Force .\runtime\bridge\in | Out-Null
New-Item -ItemType Directory -Force .\runtime\bridge\out | Out-Null
New-Item -ItemType Directory -Force .\runtime\bridge\feedback | Out-Null
New-Item -ItemType Directory -Force .\runtime\archive | Out-Null

if (-not (Test-Path ".\runtime\config.json")) {
    Copy-Item .\config.example.json .\runtime\config.json
}

Write-Host "Agente local preparado. Se a config ja veio do painel, abra .\\iniciar-vuno-robo.cmd"
