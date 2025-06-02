# PowerShell script to start Docker Desktop and wait for it to be ready
Write-Host "Starting Docker Desktop..." -ForegroundColor Green

# Start Docker Desktop if not running
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProcess) {
    Write-Host "Docker Desktop not running. Starting..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
}

# Wait for Docker to be ready
Write-Host "Waiting for Docker to be ready..." -ForegroundColor Yellow
$maxAttempts = 60
$attempt = 0

do {
    $attempt++
    Write-Host "Attempt $attempt/$maxAttempts..." -ForegroundColor Cyan
    
    try {
        $dockerInfo = docker info 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker is ready!" -ForegroundColor Green
            break
        }
    }
    catch {
        # Continue waiting
    }
    
    Start-Sleep -Seconds 5
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "Docker failed to start within the expected time. Please check Docker Desktop manually." -ForegroundColor Red
    exit 1
}

Write-Host "Docker is now ready. You can run 'docker-compose up --build'" -ForegroundColor Green
