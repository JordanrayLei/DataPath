param(
    [switch]$ConfirmTemporaryPublicExposure
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

if (-not $ConfirmTemporaryPublicExposure) {
    throw 'This command creates a temporary public HTTPS URL. Re-run with -ConfirmTemporaryPublicExposure after reviewing the risk.'
}

Push-Location $root
try {
    & scripts\check_dify_cloud_readiness.ps1
    if ($LASTEXITCODE -ne 0) {
        throw 'Dify Cloud readiness check failed.'
    }
    Write-Output 'Starting a temporary Cloudflare Quick Tunnel. Press Ctrl+C to revoke the URL.'
    & npx.cmd --yes wrangler@latest tunnel quick-start http://127.0.0.1:8000
}
finally {
    Pop-Location
}
