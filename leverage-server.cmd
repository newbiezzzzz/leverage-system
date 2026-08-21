@echo off
set "ROOT=%~dp0"
cd /d "%ROOT%"
set "PYTHONDONTWRITEBYTECODE=1"
python -B server\leverage_api.py
