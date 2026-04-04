param(
    [string]$OutputDir = ".\runtime\backups",
    [int]$RetentionDays = 14,
    [bool]$VerifyRestore = $true
)

Set-Location $PSScriptRoot

$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        } elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($key) {
            Set-Item -Path ("Env:{0}" -f $key) -Value $value
        }
    }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Python do backend nao encontrado. Rode .\install.ps1 antes."
    exit 1
}

$verifyArg = if ($VerifyRestore) { "--verify-restore" } else { "--no-verify-restore" }

& .\.venv\Scripts\python.exe .\tools\backup_and_verify.py `
    --output-dir $OutputDir `
    --retention-days $RetentionDays `
    $verifyArg

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
