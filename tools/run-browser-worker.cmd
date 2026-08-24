@echo off
setlocal
cd /d D:\Leverage
if exist "D:\development\node.js\npm-global" set "PATH=D:\development\node.js\npm-global;%PATH%"
if not exist "D:\Leverage\browser-profile" mkdir "D:\Leverage\browser-profile"
python workers\browser_worker.py "%~1" --profile="D:\Leverage\browser-profile"
endlocal
