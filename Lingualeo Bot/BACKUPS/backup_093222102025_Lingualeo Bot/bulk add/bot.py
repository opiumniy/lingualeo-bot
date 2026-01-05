import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import time
from utils import ensure_requirements
from config import get_global_cookies_path
from api_client import LingualeoAPIClient

ensure_requirements()

def add_words_to_lingualeo(csv_file, cookie_file="cookie.txt"):
    """
    Добавляет слова из CSV файла в Lingualeo с использованием общего API клиента.

    Args:
        csv_file: Путь к CSV файлу с словами и переводами.
        cookie_file: Путь к файлу с куки (глобальный).
    """
    # Используем глобальный путь к куки из config
    global_cookie_path = get_global_cookies_path()
    if cookie_file != global_cookie_path:
        print(f"Предупреждение: Используется глобальный файл куки {global_cookie_path}")
        cookie_file = global_cookie_path

    client = LingualeoAPIClient()
    if not client.load_cookies():
        print(f"Ошибка: Файл куки не найден по пути {cookie_file}")
        return

    result = client.add_words_bulk(csv_file)
    print(result)
    # Добавляем задержку между батчами, если нужно
    time.sleep(1)

if __name__ == "__main__":
    # Относительные пути для portability
    csv_file_path = "bulk add/words.csv"
    cookie_file_path = "bulk add/cookie.txt"
    add_words_to_lingualeo(csv_file_path, cookie_file_path)