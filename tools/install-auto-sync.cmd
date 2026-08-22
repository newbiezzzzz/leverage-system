@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "RUNNER=%ROOT%\tools\run-auto-sync.cmd"
set "TASK=Leverage Auto Sync"

schtasks /Create /TN "%TASK%" /SC MINUTE /MO 2 /TR "cmd.exe /c \"%RUNNER%\"" /F >nul
if errorlevel 1 (
  echo Failed to install Leverage Auto Sync.
  exit /b 1
)

call "%RUNNER%"
if errorlevel 1 (
  echo Auto-sync test run failed. Check logs\auto-sync.log.
  exit /b 1
)

echo.
echo Leverage Auto Sync installed successfully.
echo GitHub main is checked every 2 minutes.
echo Dashboard/server updates are applied automatically when the working tree is clean.
echo Logs: %ROOT%\logs\auto-sync.log
