$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Project Kernel - Cloudflare Tunnel Mode " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Start Python Backend
$PythonExe = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $PythonExe = ".\.venv\Scripts\python.exe"
    Write-Host "Using virtual environment: $PythonExe" -ForegroundColor Green
}
Write-Host "Starting Python Backend on port 8089..." -ForegroundColor Yellow
$PythonProcess = Start-Process -PassThru -NoNewWindow -FilePath $PythonExe -ArgumentList "main.py --port 8089"

# 2. Check cloudflared
$CloudflaredPath = ".\cloudflared.exe"
if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "Downloading cloudflared.exe (Cloudflare Tunnels)..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $CloudflaredPath
}

# 3. Start Cloudflared Tunnel
$LogFile = "cloudflared.log"
if (Test-Path $LogFile) { Remove-Item $LogFile }
Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Yellow
$CloudflaredProcess = Start-Process -PassThru -WindowStyle Hidden -FilePath $CloudflaredPath -ArgumentList "tunnel --url http://localhost:8089" -RedirectStandardError $LogFile

Write-Host "Waiting for tunnel to establish (this may take a few seconds)..." -ForegroundColor Yellow
$TunnelUrl = $null
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $LogFile) {
        $Matches = Select-String -Path $LogFile -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com" -AllMatches
        if ($Matches) {
            $TunnelUrl = $Matches.Matches[-1].Value
            break
        }
    }
}

if ($TunnelUrl) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host " SUCCESS! YOUR PUBLIC BACKEND URL IS:" -ForegroundColor Green
    Write-Host " $TunnelUrl " -ForegroundColor White -BackgroundColor Blue
    Write-Host "========================================================`n" -ForegroundColor Green
    Write-Host "1. Copy the URL above." -ForegroundColor Yellow
    Write-Host "2. Go to your frontend code: ui/vite-app/.env (create it if needed) or vite.config.ts" -ForegroundColor Yellow
    Write-Host "3. Set VITE_API_URL=$TunnelUrl" -ForegroundColor Yellow
    Write-Host "4. Build and deploy to GitHub Pages!" -ForegroundColor Yellow
} else {
    Write-Host "Could not extract tunnel URL. Check $LogFile for errors." -ForegroundColor Red
}

Write-Host "`nPress Ctrl+C to stop the server and tunnel." -ForegroundColor Gray
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    if ($PythonProcess) { Stop-Process -Id $PythonProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($CloudflaredProcess) { Stop-Process -Id $CloudflaredProcess.Id -Force -ErrorAction SilentlyContinue }
}
