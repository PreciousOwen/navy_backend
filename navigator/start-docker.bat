@echo off
echo Starting Docker Desktop and Django Ledger...

REM Start Docker Desktop
echo Checking if Docker Desktop is running...
tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I /N "Docker Desktop.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
) else (
    echo Docker Desktop is already running.
)

REM Wait for Docker to be ready
echo Waiting for Docker to be ready...
:WAIT_LOOP
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Docker is not ready yet, waiting...
    timeout /t 5 /nobreak >nul
    goto WAIT_LOOP
)

echo Docker is ready!
echo.
echo Now you can run:
echo   docker-compose up --build
echo.
echo Or use the Makefile commands:
echo   make up
echo   make setup
echo.
pause
