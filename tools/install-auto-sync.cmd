@echo off
setlocal
set "ROOT=%~dp1"
if "%ROOT%"=="" set "ROOT=%~dp0..\"
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SCRIPT=%ROOT%tools\leverage-auto-sync.ps1"
set "TASK=Leverage Auto Sync"

schtasks /Create /TN "%TASK%" /SC MINUTE /MO 2 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT%\" -Root \"%ROOT%\"" /F >nul
if errorlevel 1 (
  echo Failed to install Leverage Auto Sync.
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT%" -Root "%ROOT%"

echo.
echo Leverage Auto Sync installed.
echo GitHub main is checked every 2 minutes.
echo Dashboard/server updates are applied automatically when the working tree is clean.
echo Logs: %ROOT%logs\auto-sync.log
