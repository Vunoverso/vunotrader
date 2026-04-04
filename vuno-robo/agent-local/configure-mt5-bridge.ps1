param(
    [string]$ConfigPath = ".\runtime\config.json",
    [string]$BridgeName = "",
    [string]$CommonFilesPath = "$env:APPDATA\MetaQuotes\Terminal\Common\Files"
)

Set-Location $PSScriptRoot

function Set-ConfigValue {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Value
    )

    if ($Object.PSObject.Properties[$Name]) {
        $Object.$Name = $Value
        return
    }

    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($BridgeName)) {
    $BridgeName = [string]$config.bridge_name
}
if ([string]::IsNullOrWhiteSpace($BridgeName)) {
    $BridgeName = "VunoBridge"
}

$bridgeRoot = Join-Path $CommonFilesPath $BridgeName
$snapshotDir = Join-Path $bridgeRoot "in"
$commandDir = Join-Path $bridgeRoot "out"
$feedbackDir = Join-Path $bridgeRoot "feedback"
$metadataDir = Join-Path $bridgeRoot "metadata"
$archiveDir = Join-Path $PSScriptRoot "runtime\archive"

New-Item -ItemType Directory -Force $snapshotDir | Out-Null
New-Item -ItemType Directory -Force $commandDir | Out-Null
New-Item -ItemType Directory -Force $feedbackDir | Out-Null
New-Item -ItemType Directory -Force $metadataDir | Out-Null
New-Item -ItemType Directory -Force $archiveDir | Out-Null

Set-ConfigValue -Object $config -Name "bridge_name" -Value $BridgeName
Set-ConfigValue -Object $config -Name "snapshot_dir" -Value $snapshotDir
Set-ConfigValue -Object $config -Name "command_dir" -Value $commandDir
Set-ConfigValue -Object $config -Name "feedback_dir" -Value $feedbackDir
Set-ConfigValue -Object $config -Name "metadata_dir" -Value $metadataDir
Set-ConfigValue -Object $config -Name "archive_dir" -Value $archiveDir

$config | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $ConfigPath

Write-Host "Bridge configurado para MT5 em: $bridgeRoot"
Write-Host "Use o mesmo valor '$BridgeName' no input InpBridgeRoot do EA."
