param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root '.env.example'
$target = Join-Path $root '.env'

if ((Test-Path -LiteralPath $target) -and -not $Force) {
    throw '.env already exists. Re-run with -Force only if rotating all local demo secrets is intended.'
}

function New-HexSecret([int]$Bytes) {
    $buffer = [byte[]]::new($Bytes)
    [Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return [Convert]::ToHexString($buffer).ToLowerInvariant()
}

$content = Get-Content -LiteralPath $source -Raw -Encoding utf8
$content = $content -replace '(?m)^ENVIRONMENT=.*$', 'ENVIRONMENT=dify_cloud_demo'
$content = $content -replace '(?m)^CHATBI_API_TOKEN=.*$', "CHATBI_API_TOKEN=$(New-HexSecret 32)"
$content = $content -replace '(?m)^DEMO_IDENTITY_TOKEN=.*$', "DEMO_IDENTITY_TOKEN=$(New-HexSecret 24)"
$content = $content -replace '(?m)^SIGNING_SECRET=.*$', "SIGNING_SECRET=$(New-HexSecret 48)"

[IO.File]::WriteAllText($target, $content, [Text.UTF8Encoding]::new($false))

Write-Output 'Created .env with rotated local demo secrets.'
Write-Output 'Open .env locally and copy CHATBI_API_TOKEN and DEMO_IDENTITY_TOKEN into Dify. Do not send them in chat.'
Write-Output 'Restart the FastAPI process before starting the tunnel.'
