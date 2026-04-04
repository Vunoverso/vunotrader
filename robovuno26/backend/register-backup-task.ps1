param(
    [string]$TaskName = "VunoTraderBackup",
    [string]$DailyAt = "03:00",
    [int]$RetentionDays = 14,
    [bool]$VerifyRestore = $true
)

Set-Location $PSScriptRoot

$scriptPath = Join-Path $PSScriptRoot "backup-db.ps1"
if (-not (Test-Path $scriptPath)) {
    Write-Error "Script de backup nao encontrado em $scriptPath"
    exit 1
}

$verifySegment = "-VerifyRestore:$VerifyRestore"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -RetentionDays $RetentionDays $verifySegment"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Description "Backup automatico do banco Vuno Trader com restore-check opcional" `
    -Force | Out-Null

Write-Host "Tarefa registrada: $TaskName (diariamente as $DailyAt)"
