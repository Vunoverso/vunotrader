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

$appEnv = if ($env:APP_ENV) { $env:APP_ENV.Trim().ToLowerInvariant() } else { "development" }
$apiHost = if ($env:API_HOST) { $env:API_HOST.Trim() } else { "127.0.0.1" }
$port = if ($env:API_PORT) { $env:API_PORT.Trim() } else { "8000" }
$workers = if ($env:UVICORN_WORKERS) { $env:UVICORN_WORKERS.Trim() } else { "2" }

if ($appEnv -eq "production" -or $appEnv -eq "staging") {
    Write-Host "Iniciando backend em modo $appEnv (host=$apiHost port=$port workers=$workers)"
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host $apiHost --port $port --workers $workers
} else {
    Write-Host "Iniciando backend em modo development (reload habilitado)"
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host $apiHost --port $port
}
