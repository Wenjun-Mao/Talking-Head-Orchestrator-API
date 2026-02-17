param(
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vendorDir = Join-Path $scriptDir "vendor"
$signozDir = Join-Path $vendorDir "signoz"
$signozCompose = Join-Path $signozDir "deploy/docker/docker-compose.yaml"

git config --global core.longpaths true | Out-Null

if (!(Test-Path $vendorDir)) {
    New-Item -ItemType Directory -Path $vendorDir | Out-Null
}

if (!(Test-Path $signozDir)) {
    Write-Host "Cloning SigNoz ($Branch) to $signozDir ..."
    git clone -b $Branch https://github.com/SigNoz/signoz.git $signozDir
} else {
    Write-Host "SigNoz repo already exists at $signozDir"
}

if (!(Test-Path $signozCompose)) {
    throw "SigNoz compose file not found: $signozCompose"
}

Write-Host "Starting SigNoz from $signozCompose ..."
docker compose -f $signozCompose up -d --remove-orphans

Write-Host "SigNoz startup command submitted. Open: http://localhost:8080"
