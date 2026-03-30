param(
  [string]$VenvPath = ".venv-brain311",
  [string]$RequirementsFile = "brain-requirements.txt"
)

$ErrorActionPreference = "Stop"

function Write-Step($message) {
  Write-Host "`n==> $message" -ForegroundColor Cyan
}

function Fail($message) {
  Write-Host "`n[ERRO] $message" -ForegroundColor Red
  exit 1
}

Write-Step "Bootstrap do Brain Python (venv 3.11)"

if (-not (Test-Path $RequirementsFile)) {
  Fail "Arquivo de dependencias nao encontrado: $RequirementsFile"
}

Write-Step "Validando Python 3.11 no sistema"
$py311Check = cmd /c 'py -3.11 -c "import sys; print(sys.executable)" 2>nul'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($py311Check)) {
  Fail "Python 3.11 nao encontrado. Instale Python 3.11 e rode novamente. Dica: winget install Python.Python.3.11"
}

$python311Path = $py311Check.Trim()
Write-Host "Python 3.11: $python311Path" -ForegroundColor Green

Write-Step "Criando venv em $VenvPath"
if (Test-Path $VenvPath) {
  Write-Host "Venv existente detectada. Recriando..." -ForegroundColor Yellow
  Remove-Item -Recurse -Force $VenvPath
}

& py -3.11 -m venv $VenvPath
if ($LASTEXITCODE -ne 0) {
  Fail "Falha ao criar venv em $VenvPath"
}

$venvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Fail "Python da venv nao encontrado em $venvPython"
}

Write-Step "Atualizando pip/setuptools/wheel"
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
  Fail "Falha ao atualizar pip/setuptools/wheel"
}

Write-Step "Instalando dependencias do Brain"
& $venvPython -m pip install -r $RequirementsFile
if ($LASTEXITCODE -ne 0) {
  Fail "Falha na instalacao de dependencias"
}

Write-Step "Validando import do brain-py"
& $venvPython -c "import brainpy as bp; print('brainpy', bp.__version__)"
if ($LASTEXITCODE -ne 0) {
  Fail "brain-py nao importou corretamente na venv 3.11"
}

Write-Step "Validando integracao com vunotrader_brain.py"
$repoRoot = Split-Path -Parent $PSScriptRoot
$bootstrapCheck = @'
import os
import sys
sys.path.insert(0, r"REPO_ROOT")
os.environ["ENABLE_BRAINPY"] = "1"
import vunotrader_brain as v
print("BRAINPY_AVAILABLE=", v.BRAINPY_AVAILABLE)
print("IMPORT_ERROR=", v.BRAINPY_IMPORT_ERROR or "none")
if not v.BRAINPY_AVAILABLE:
    raise SystemExit(1)
'@
$bootstrapCheck = $bootstrapCheck.Replace("REPO_ROOT", $repoRoot)

& $venvPython -c $bootstrapCheck
if ($LASTEXITCODE -ne 0) {
  Fail "Integracao com vunotrader_brain.py nao validou com ENABLE_BRAINPY=1"
}

Write-Host "`n[OK] Bootstrap finalizado com sucesso." -ForegroundColor Green
Write-Host "Para ativar a venv: .\$VenvPath\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Para rodar o brain:  .\$VenvPath\Scripts\python.exe .\vunotrader_brain.py" -ForegroundColor Green
