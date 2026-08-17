@echo off
set "ROOT=%~dp0"
cd /d "%ROOT%"
python server\leverage_api.py
