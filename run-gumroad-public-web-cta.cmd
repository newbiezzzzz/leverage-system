@echo off
set "ROOT=%~dp0"
cd /d "%ROOT%"
python "%ROOT%workers\gumroad_cta_worker.py" "Update the Gumroad listing so buyers can access Leverage's public web calculator and verify the clickable public-web CTA."
if errorlevel 1 (
  echo.
  echo Gumroad CTA update failed. Review the output above.
  exit /b 1
)
echo.
echo Gumroad public-web CTA update and verification completed.
