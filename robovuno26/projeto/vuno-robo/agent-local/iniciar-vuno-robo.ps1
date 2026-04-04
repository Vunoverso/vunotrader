param(
    [string]$PythonExe = "python",
    [string]$BridgeName = "",
    [switch]$ForcePython
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$binaryPath = Join-Path $PSScriptRoot "dist\vuno-agent.exe"
$configPath = ".\runtime\config.json"

function Test-StaleBinary {
    param([string]$BinaryPath)

    if (-not (Test-Path $BinaryPath)) {
        return $false
    }

    $binaryWriteTime = (Get-Item $BinaryPath).LastWriteTimeUtc
    $sourcePaths = @(
        (Join-Path $PSScriptRoot "start_agent.py"),
        (Join-Path $PSScriptRoot "app\*.py")
    )

    $latestSource = Get-ChildItem $sourcePaths -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if (-not $latestSource) {
        return $false
    }

    return $latestSource.LastWriteTimeUtc -gt $binaryWriteTime
}

$useBinary = (Test-Path $binaryPath) -and -not $ForcePython
if ($useBinary -and (Test-StaleBinary -BinaryPath $binaryPath)) {
    Write-Host "Executavel encontrado, mas o codigo-fonte esta mais novo. Vou iniciar pelo Python para evitar binario desatualizado."
    $useBinary = $false
}

if ($useBinary) {
    Write-Host "Executavel do agente encontrado. Python nao sera necessario neste start."
} else {
    Write-Host "Preparando ambiente do Vuno Robo..."
    & .\install.ps1 -PythonExe $PythonExe
}

Write-Host "Configurando bridge com o MT5..."
& .\configure-mt5-bridge.ps1 -ConfigPath $configPath -BridgeName $BridgeName

if ($useBinary) {
    Write-Host "Iniciando agente local pelo executavel..."
    & $binaryPath --config $configPath
    exit $LASTEXITCODE
}

Write-Host "Iniciando agente local pelo ambiente Python..."
& .\run-agent.ps1