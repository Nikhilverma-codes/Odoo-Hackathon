param(
    [switch]$SkipBuild,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}

if (-not $SkipBuild) {
    Write-Host 'Building the frontend...'
    Push-Location (Join-Path $root 'frontend')
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    }
    finally {
        Pop-Location
    }
}

$url = "http://127.0.0.1:$Port"
Write-Host ''
Write-Host "Brightloop is starting at $url"
Write-Host 'Admin:    admin@brightloop.io / Admin@1234'
Write-Host 'Staff:    sales@brightloop.io / Staff@1234'
Write-Host 'Customer: billing@acme-retail.com / Customer@1234'
Write-Host ''
Write-Host 'Demo tip: open Invoices -> Run billing -> Next 30 days -> Preview -> Run billing.'
Write-Host 'Press Ctrl+C to stop.'

Push-Location $root
try {
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
