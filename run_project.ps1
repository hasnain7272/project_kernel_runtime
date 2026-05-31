$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Project Kernel - Unified Runner " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 0. Clean up previous instances specific to THIS project
$PythonPidFile = "python.pid"
$CloudflaredPidFile = "cloudflared.pid"

if (Test-Path $PythonPidFile) {
    $OldPid = Get-Content $PythonPidFile
    Write-Host "Cleaning up old python process tree (PID: $OldPid)..." -ForegroundColor Yellow
    cmd.exe /c "taskkill /F /T /PID $OldPid" | Out-Null
    Remove-Item $PythonPidFile -Force -ErrorAction SilentlyContinue
}

if (Test-Path $CloudflaredPidFile) {
    $OldPid = Get-Content $CloudflaredPidFile
    Write-Host "Cleaning up old cloudflared process tree (PID: $OldPid)..." -ForegroundColor Yellow
    cmd.exe /c "taskkill /F /T /PID $OldPid" | Out-Null
    Remove-Item $CloudflaredPidFile -Force -ErrorAction SilentlyContinue
}

# 1. Start Python Backend
$PythonExe = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $PythonExe = ".\.venv\Scripts\python.exe"
    Write-Host "Using virtual environment: $PythonExe" -ForegroundColor Green
}
Write-Host "Starting Python Backend on port 8089 (with hot-reload)..." -ForegroundColor Yellow
$PythonProcess = Start-Process -PassThru -NoNewWindow -FilePath $PythonExe -ArgumentList "main.py --port 8089"
$PythonProcess.Id | Out-File -FilePath $PythonPidFile -Encoding ASCII

# 2. Check cloudflared
$CloudflaredPath = ".\cloudflared.exe"
if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "Downloading cloudflared.exe (Cloudflare Tunnels)..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $CloudflaredPath
}

# 3. Start Cloudflared Tunnel
$LogFile = "cloudflared.log"
if (Test-Path $LogFile) { Remove-Item $LogFile -Force -ErrorAction SilentlyContinue }
Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Yellow
$CloudflaredProcess = Start-Process -PassThru -WindowStyle Hidden -FilePath $CloudflaredPath -ArgumentList "tunnel --url http://localhost:8089" -RedirectStandardError $LogFile
$CloudflaredProcess.Id | Out-File -FilePath $CloudflaredPidFile -Encoding ASCII

Write-Host "Waiting for tunnel to establish (this may take a few seconds)..." -ForegroundColor Yellow
$TunnelUrl = $null
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Path $LogFile) {
        $Matches = Select-String -Path $LogFile -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com" -AllMatches
        if ($Matches) {
            $TunnelUrl = $Matches.Matches[-1].Value
            break
        }
    }
}

if (-not $TunnelUrl) {
    Write-Host "Could not extract tunnel URL. Check $LogFile for errors." -ForegroundColor Red
    if ($PythonProcess) { Stop-Process -Id $PythonProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($CloudflaredProcess) { Stop-Process -Id $CloudflaredProcess.Id -Force -ErrorAction SilentlyContinue }
    exit 1
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host " BACKEND ONLINE AT: $TunnelUrl" -ForegroundColor White -BackgroundColor Blue
Write-Host "========================================================`n" -ForegroundColor Green

Write-Host "-> Deploying frontend with new URL..." -ForegroundColor Yellow
# 4. Update .env
$EnvPath = "ui/vite-app/.env"
Set-Content -Path $EnvPath -Value "VITE_API_URL=$TunnelUrl"
Write-Host "-> Wrote $TunnelUrl to $EnvPath" -ForegroundColor Green

# 5. Build and Deploy Frontend
Push-Location "ui/vite-app"

Write-Host "-> Installing npm dependencies..." -ForegroundColor Yellow
npm install | Out-Null

Write-Host "-> Building Vite App..." -ForegroundColor Yellow
$env:VITE_API_URL = $TunnelUrl
npm run build | Out-Null

# Deploy using raw git commands
Write-Host "-> Pushing to GitHub Pages..." -ForegroundColor Yellow
Set-Location "dist"
$OriginalErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
if (Test-Path ".git") { Remove-Item -Recurse -Force ".git" -ErrorAction SilentlyContinue }
git init | Out-Null
git checkout -b gh-pages 2>&1 | Out-Null
git add -A
git commit -m "Automated Deployment" | Out-Null
if (git remote) { git remote set-url origin https://github.com/hasnain7272/project_kernel_runtime.git 2>&1 | Out-Null } else { git remote add origin https://github.com/hasnain7272/project_kernel_runtime.git 2>&1 | Out-Null }
git push -f origin gh-pages 2>&1 | Out-Null
$ErrorActionPreference = $OriginalErrorAction
Set-Location ".."

Pop-Location
Write-Host "=========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE! " -ForegroundColor Green
Write-Host " Your UI is now live on GitHub pages and connected to your local backend." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

Write-Host "`nBackend is currently running. Press Ctrl+C to safely stop the server and tunnel." -ForegroundColor Gray
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "Shutting down backend and tunnel..." -ForegroundColor Yellow
    if ($PythonProcess) { cmd.exe /c "taskkill /F /T /PID $($PythonProcess.Id)" | Out-Null }
    if ($CloudflaredProcess) { cmd.exe /c "taskkill /F /T /PID $($CloudflaredProcess.Id)" | Out-Null }
    if (Test-Path $PythonPidFile) { Remove-Item $PythonPidFile -Force -ErrorAction SilentlyContinue }
    if (Test-Path $CloudflaredPidFile) { Remove-Item $CloudflaredPidFile -Force -ErrorAction SilentlyContinue }
}
