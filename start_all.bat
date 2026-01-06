@echo off
echo Starting Lingualeo Bot and Update Agent...
echo.

cd /d "%~dp0"

start "Lingualeo Bot" cmd /k "cd /d \"%~dp0Lingualeo Bot\lingualeo_pyth\" && python tg_bot.py"

timeout /t 3 /nobreak >nul

start "Update Agent" cmd /k "cd /d \"%~dp0\" && python deploy_agent.py"

echo.
echo Both processes started in separate windows.
echo Close this window or press any key to exit.
pause
