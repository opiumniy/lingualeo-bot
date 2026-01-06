@echo off
echo Starting Lingualeo Bot and Update Agent...

start "Lingualeo Bot" run_bot.bat
timeout /t 2 /nobreak > nul
start "Update Agent" run_updater.bat

echo Both processes started in separate windows.
pause
