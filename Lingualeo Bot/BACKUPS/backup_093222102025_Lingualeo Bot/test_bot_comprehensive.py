#!/usr/bin/env python3
"""
Комплексный тестовый скрипт для проверки модернизированного бота
"""
import asyncio
import sys
import os
import json
import logging
from pathlib import Path

# Настройка логирования для теста
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем текущую директорию в путь для импортов
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from api_client import LingualeoAPIClient
    from config import get_user_cookies_path, get_global_cookies_path
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    sys.exit(1)

class BotTester:
    """Класс для тестирования функций бота"""

    def __init__(self):
        self.test_user_id = 531253663

    async def test_authentication(self):
        """Тестируем улучшенную аутентификацию"""
        print("\n=== TESTING AUTHENTICATION ===")

        client = LingualeoAPIClient(user_id=self.test_user_id)

        # Тестируем загрузку cookies с fallback
        print("Loading cookies with fallback mechanism...")
        success = await client.load_user_cookies_async(self.test_user_id)

        if success:
            print("Cookies загружены успешно!")
            print(f"  Длина cookies: {len(client.cookies)} символов")
            print(f"  Заголовки установлены: {'Cookie' in client.headers}")

            # Проверяем содержимое cookies
            if 'remember=' in client.cookies:
                print("Найден токен remember")
            if 'userid=' in client.cookies:
                print("Найден user ID")

            return True
        else:
            print("Не удалось загрузить cookies")
            self._check_cookie_files()
            return False

    def _check_cookie_files(self):
        """Проверяем наличие файлов cookies"""
        print("Проверяем файлы cookies:")

        # Пользовательский файл
        user_path = get_user_cookies_path(self.test_user_id)
        if os.path.exists(user_path):
            size = os.path.getsize(user_path)
            print(f"  Пользовательский файл: {user_path} ({size} bytes)")
        else:
            print(f"  Пользовательский файл НЕ найден: {user_path}")

        # Глобальный файл
        global_path = get_global_cookies_path()
        if os.path.exists(global_path):
            size = os.path.getsize(global_path)
            print(f"  Глобальный файл: {global_path} ({size} bytes)")
        else:
            print(f"  Глобальный файл НЕ найден: {global_path}")

    async def test_training_results(self):
        """Тестируем работу с результатами тренировки"""
        print("\n=== TESTING TRAINING RESULTS ===")

        # Создаем тестовые результаты
        test_results = {
            "12345": 1,  # правильный ответ
            "67890": 2,  # неправильный ответ
            "11111": 1,
            "22222": 2
        }

        # Сохраняем в файл
        results_file = f"lingualeo_pyth/training_results_{self.test_user_id}.json"
        try:
            os.makedirs("lingualeo_pyth", exist_ok=True)
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, ensure_ascii=False, indent=2)
            print(f"Тестовые результаты сохранены: {len(test_results)} ответов")
        except Exception as e:
            print(f"Ошибка сохранения результатов: {e}")
            return False

        # Загружаем результаты
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                loaded_results = json.load(f)
            print(f"Результаты загружены: {len(loaded_results)} ответов")

            if loaded_results == test_results:
                print("Данные совпадают после загрузки")
            else:
                print("Данные не совпадают после загрузки")
                return False

        except Exception as e:
            print(f"Ошибка загрузки результатов: {e}")
            return False

        # Тестируем отправку на сервер
        print("Отправляем результаты на сервер...")
        client = LingualeoAPIClient(user_id=self.test_user_id)

        if await client.load_user_cookies_async(self.test_user_id):
            try:
                response = client.process_training_answer_batch(test_results)
                print("Результаты успешно отправлены на сервер")
                print(f"  Тип ответа: {type(response)}")

                # Очищаем файл после успешной отправки
                try:
                    os.remove(results_file)
                    print("Файл результатов очищен после отправки")
                except Exception as e:
                    print(f"Ошибка очистки файла: {e}")

                return True

            except Exception as e:
                print(f"Ошибка отправки на сервер: {e}")
                return False
        else:
            print("Не удалось загрузить cookies для отправки")
            return False

    async def run_all_tests(self):
        """Запускаем все тесты"""
        print("STARTING COMPREHENSIVE BOT TESTING")
        print("=" * 50)

        results = []

        # Тест аутентификации
        auth_ok = await self.test_authentication()
        results.append(("Аутентификация", auth_ok))

        # Тест результатов тренировки
        if auth_ok:
            results_ok = await self.test_training_results()
            results.append(("Результаты тренировки", results_ok))
        else:
            results.append(("Результаты тренировки", False))

        # Выводим итоги
        print("\n" + "=" * 50)
        print("ИТОГИ ТЕСТИРОВАНИЯ:")
        print("=" * 50)

        all_passed = True
        for test_name, passed in results:
            status = "ПРОЙДЕН" if passed else "ПРОВАЛЕН"
            print(f"{test_name:25} {status}")
            if not passed:
                all_passed = False

        print("=" * 50)
        if all_passed:
            print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Бот готов к работе.")
        else:
            print("НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Проверьте конфигурацию.")

        return all_passed

async def main():
    """Главная функция"""
    tester = BotTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())