@echo off
schtasks /Delete /TN "Leverage Local API" /F >nul 2>&1
if errorlevel 1 (
  echo Leverage Local API auto-start was not registered or is already disabled.
  exit /b 0
)
echo Leverage Local API auto-start disabled.
