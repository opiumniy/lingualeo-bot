@echo off
echo === Lingualeo Bot with Auto-Update ===
echo.
echo This will start the bot with automatic update checking.
echo The bot will restart automatically when new code is pushed to GitHub.
echo.
echo Press Ctrl+C to stop.
echo.

cd /d "%~dp0"
python deploy_agent.py
