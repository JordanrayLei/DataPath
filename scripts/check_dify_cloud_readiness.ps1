$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root '.env'
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw 'Missing .env. Run scripts\prepare_dify_cloud_demo.ps1 first.'
}

$content = Get-Content -LiteralPath $envPath -Raw -Encoding utf8
$forbidden = @(
    'CHATBI_API_TOKEN=dev-chatbi-token',
    'DEMO_IDENTITY_TOKEN=demo-server-issued-token',
    'SIGNING_SECRET=replace-this-local-signing-secret'
)
foreach ($value in $forbidden) {
    if ($content.Contains($value)) {
        throw "Unsafe default credential remains: $($value.Split('=')[0])"
    }
}
if (-not $content.Contains('ENVIRONMENT=dify_cloud_demo')) {
    throw 'ENVIRONMENT must be dify_cloud_demo so public API docs stay disabled.'
}

Push-Location $root
try {
    & $python scripts\validate_contracts.py
    if ($LASTEXITCODE -ne 0) {
        throw 'Contract validation failed.'
    }
    $health = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5
    if ($health.status -ne 'ok') {
        throw 'Local FastAPI health check did not return ok.'
    }
    try {
        Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 5 | Out-Null
        throw 'API docs are still public. Restart FastAPI after loading the new .env.'
    }
    catch {
        if ($_.Exception.Message -like 'API docs are still public*') {
            throw
        }
        if ($_.Exception.Response.StatusCode.value__ -ne 404) {
            throw
        }
    }
}
finally {
    Pop-Location
}

Write-Output 'PASS: Dify Cloud demo readiness checks.'
