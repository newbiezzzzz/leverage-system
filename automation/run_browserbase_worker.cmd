@echo off
setlocal
set "ROOT=%~dp0"
if not defined BROWSERBASE_API_KEY (
  echo BROWSERBASE_API_KEY is not configured.
  exit /b 2
)
if not exist "%ROOT%node_modules\@browserbasehq\stagehand" (
  echo Installing web automation dependencies...
  pushd "%ROOT%"
  call npm install --no-fund --no-audit
  if errorlevel 1 (
    popd
    exit /b 3
  )
  popd
)
node "%ROOT%browserbase_stagehand_worker.mjs"
exit /b %errorlevel%
