@echo off
setlocal
set "ROOT=%~dp0"

where pythonw.exe >nul 2>&1
if errorlevel 1 (
  echo Python with pythonw.exe was not found on PATH.
  echo Install Python or add it to PATH, then run this setup again.
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$root='%ROOT%'; $python=(Get-Command pythonw.exe -ErrorAction Stop).Source; $script=Join-Path $root 'server\leverage_api.py'; $action=New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '"'); $trigger=New-ScheduledTaskTrigger -AtLogOn; $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -StartWhenAvailable; Register-ScheduledTask -TaskName 'Leverage Local API' -Action $action -Trigger $trigger -Settings $settings -Description 'Starts the local Leverage Control Plane bridge at Windows logon.' -Force | Out-Null"
if errorlevel 1 (
  echo Failed to register Leverage Local API auto-start.
  exit /b 1
)

echo.
echo Leverage Local API auto-start is enabled.
echo The bridge will start automatically when you sign in to Windows.
echo Money movement remains PROTECTED.
endlocal
