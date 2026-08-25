@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo LEVERAGE LOCAL REFRESH
echo ========================================
echo.

echo [1/5] Pulling latest Leverage state...
git pull --ff-only origin main
if errorlevel 1 (
  echo.
  echo REFRESH BLOCKED: git pull failed.
  echo Resolve the local git state, then run this again.
  exit /b 1
)

echo.
echo [2/5] Migrating mutable runtime project state...
python -m control_plane.migrate_runtime_state
if errorlevel 1 exit /b 1

echo.
echo [3/5] Verifying project registry...
python -m control_plane.company_core
if errorlevel 1 exit /b 1

echo.
echo [4/5] Restarting local API on port 8765...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
  echo Stopping Leverage API PID %%P
  taskkill /PID %%P /F >nul 2>&1
)

echo.
echo [5/5] Starting Leverage Local API...
if exist "%~dp0leverage-server.cmd" (
  call "%~dp0leverage-server.cmd"
) else (
  echo leverage-server.cmd was not found.
  echo Start the Leverage server manually from this folder.
  exit /b 2
)
