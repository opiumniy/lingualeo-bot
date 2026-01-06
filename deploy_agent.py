#!/usr/bin/env python3
"""
Auto-update agent for Lingualeo Telegram Bot.
Checks GitHub for updates and restarts the bot if new code is available.
Works on Windows without PM2.
"""

import subprocess
import sys
import os
import time
import signal

BOT_SCRIPT = os.path.join("Lingualeo Bot", "lingualeo_pyth", "tg_bot.py")
CHECK_INTERVAL = 60  # seconds

bot_process = None


def check_for_updates():
    """Check if there are new commits on origin/main"""
    try:
        subprocess.run(["git", "fetch"], capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "rev-list", "HEAD...origin/main", "--count"],
            capture_output=True, text=True, timeout=10
        )
        count = int(result.stdout.strip())
        return count > 0
    except Exception as e:
        print(f"Error checking updates: {e}")
        return False


def pull_updates():
    """Pull latest code from GitHub"""
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=60)
        print(result.stdout)
        if result.returncode == 0:
            return True
        print(f"Git pull error: {result.stderr}")
        return False
    except Exception as e:
        print(f"Error pulling updates: {e}")
        return False


def start_bot():
    """Start the bot as a subprocess"""
    global bot_process
    if bot_process and bot_process.poll() is None:
        print("Bot is already running")
        return
    
    print("Starting bot...")
    bot_process = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    print(f"Bot started with PID: {bot_process.pid}")


def stop_bot():
    """Stop the bot subprocess"""
    global bot_process
    if bot_process and bot_process.poll() is None:
        print("Stopping bot...")
        bot_process.terminate()
        try:
            bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            bot_process.kill()
            bot_process.wait()
        print("Bot stopped")
    bot_process = None


def restart_bot():
    """Restart the bot"""
    print("Restarting bot...")
    stop_bot()
    time.sleep(2)
    start_bot()


def main():
    print("=== Lingualeo Bot Deploy Agent ===")
    print(f"Checking for updates every {CHECK_INTERVAL} seconds")
    
    start_bot()
    
    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            print("\n🔍 Проверяю обновления...")
            
            if check_for_updates():
                print("🚀 Новый код! Обновляюсь...")
                if pull_updates():
                    print("♻️ Перезапускаю бота...")
                    restart_bot()
            else:
                print("✅ Код актуален")
    
    except KeyboardInterrupt:
        print("\nStopping...")
        stop_bot()
        print("Goodbye!")


if __name__ == "__main__":
    main()
