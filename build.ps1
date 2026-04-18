# build.ps1 — Production Build & Deploy
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ViteDir = Join-Path $ProjectRoot "ui\vite-app"

Write-Host "[1/2] Building Vite React Dashboard..."
Set-Location $ViteDir
npm run build

Write-Host "[2/2] Build complete!"
Write-Host "  Local dev:  cd $ViteDir && npm run dev"
Write-Host "  Backend:    cd $ProjectRoot && python -m uvicorn src.api.fastapi_gateway:app --port 8089 --reload"
Write-Host "  Production: cd $ProjectRoot && docker compose up -d"
