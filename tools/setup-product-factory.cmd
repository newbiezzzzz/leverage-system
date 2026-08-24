@echo off
setlocal
cd /d %~dp0..

echo === Leverage Product Factory v2 setup ===
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required for local n8n. Install Node.js LTS, then rerun this script.
  exit /b 1
)

where n8n >nul 2>nul
if errorlevel 1 (
  echo Installing n8n locally...
  call npm install --location=global n8n
  if errorlevel 1 exit /b 1
)

if not exist .factory\ mkdir .factory
if not exist .factory\n8n-data\ mkdir .factory\n8n-data\

echo Factory files are installed in the repository.
echo Start local n8n with:
echo   n8n start

echo Then import:
echo   n8n\leverage-product-factory-dry-run.json

echo The imported workflow is inactive by default and is a dry-run only.
exit /b 0
