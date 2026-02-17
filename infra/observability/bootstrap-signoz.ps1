$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$signozCompose = Join-Path $scriptDir "signoz/docker/docker-compose.yaml"

if (!(Test-Path $signozCompose)) {
    throw "SigNoz compose file not found: $signozCompose"
}

Write-Host "Starting SigNoz from $signozCompose ..."
docker compose -p signoz -f $signozCompose up -d --remove-orphans

Write-Host "SigNoz startup command submitted. Open: http://localhost:8080"
