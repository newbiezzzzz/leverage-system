@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SCRIPT=%ROOT%\tools\leverage-auto-sync.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT%" -Root "%ROOT%"
exit /b %ERRORLEVEL%
