param (
    [string]$TunnelUrl = ""
)
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Frontend Auto-Deploy to GitHub Pages    " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

if ($TunnelUrl -eq "") {
    # Try to automatically grab it from the log
    $LogFile = "cloudflared.log"
    if (Test-Path $LogFile) {
        $Matches = Select-String -Path $LogFile -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com" -AllMatches
        if ($Matches) {
            $TunnelUrl = $Matches.Matches[-1].Value
        }
    }
}

if ($TunnelUrl -eq "") {
    Write-Host "Error: No Tunnel URL found." -ForegroundColor Red
    Write-Host "Make sure .\start_with_tunnel.ps1 is running, or provide the URL manually:" -ForegroundColor Yellow
    Write-Host ".\deploy_frontend.ps1 -TunnelUrl 'https://...trycloudflare.com'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Target API URL: $TunnelUrl" -ForegroundColor Green

# 1. Update .env
$EnvPath = "ui/vite-app/.env"
Set-Content -Path $EnvPath -Value "VITE_API_URL=$TunnelUrl"
Write-Host "-> Wrote $TunnelUrl to $EnvPath" -ForegroundColor Green

# 2. Build Frontend
Push-Location "ui/vite-app"

Write-Host "-> Installing npm dependencies..." -ForegroundColor Yellow
npm install

Write-Host "-> Building Vite App..." -ForegroundColor Yellow
$env:VITE_API_URL = $TunnelUrl
npm run build

# 3. Deploy using raw git commands (bypassing gh-pages long-path bug on Windows)
Write-Host "-> Deploying to GitHub Pages..." -ForegroundColor Yellow
Set-Location "dist"
git init
git checkout -b gh-pages
git add -A
git commit -m "Automated Deployment"
if (git remote) { git remote set-url origin https://github.com/hasnain7272/project_kernel_runtime.git } else { git remote add origin https://github.com/hasnain7272/project_kernel_runtime.git }
git push -f origin gh-pages
Set-Location ".."

Pop-Location
Write-Host "=========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE! " -ForegroundColor Green
Write-Host " Your UI is now live on GitHub pages and connected to your local backend." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
