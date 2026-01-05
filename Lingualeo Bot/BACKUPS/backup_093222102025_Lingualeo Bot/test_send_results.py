#!/usr/bin/env python3
"""
Тестовый скрипт для проверки быстрого фикса аутентификации
"""
import asyncio
import sys
import os

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_client import LingualeoAPIClient

async def test_authentication():
    """Тестируем аутентификацию с нашим быстрым фиксом"""
    print("Testing quick authentication fix...")

    # Создаем клиент для пользователя 531253663
    client = LingualeoAPIClient(user_id=531253663)

    # Тестируем загрузку cookies
    print("Loading cookies for user 531253663...")
    success = await client.load_user_cookies_async(531253663)

    if success:
        print("SUCCESS! Cookies loaded successfully!")
        print(f"Cookies: {client.cookies[:50]}...")
        print(f"Headers set: {'Cookie' in client.headers}")

        # Тестируем отправку результатов тренировки
        print("\nTesting training results submission...")
        try:
            # Загружаем тестовые результаты
            if os.path.exists('lingualeo_pyth/training_results_531253663.json'):
                import json
                with open('lingualeo_pyth/training_results_531253663.json', 'r', encoding='utf-8') as f:
                    training_results = json.load(f)

                print(f"Found {len(training_results)} results to send")

                # Отправляем результаты
                response = client.process_training_answer_batch(training_results)
                print("Results successfully sent to server!")
                print(f"Server response: {response}")

                # Очищаем файл после успешной отправки
                os.remove('lingualeo_pyth/training_results_531253663.json')
                print("Results file cleared")

            else:
                print("Results file not found")

        except Exception as e:
            print(f"Error sending results: {e}")

    else:
        print("FAILURE! Could not load cookies")
        print("Checking available cookie files:")

        # Проверяем пользовательский файл
        user_cookies_path = f"User_Cookies/{531253663}_cookies.txt"
        if os.path.exists(user_cookies_path):
            print(f"User cookies file found: {user_cookies_path}")
        else:
            print(f"User cookies file NOT found: {user_cookies_path}")

        # Проверяем глобальный файл
        global_cookies_path = "cookies_current.txt"
        if os.path.exists(global_cookies_path):
            print(f"Global cookies file found: {global_cookies_path}")
        else:
            print(f"Global cookies file NOT found: {global_cookies_path}")

if __name__ == "__main__":
    asyncio.run(test_authentication())