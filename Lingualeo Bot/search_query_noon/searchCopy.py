import requests
import csv
import json
import os
import shlex # Библиотека для парсинга командной строки
import time   # Добавлено для пауз
import random # Добавлено для случайного времени паузы

# --- КОНФИГУРАЦИЯ ---
URL = "https://admanager.noon.partners/_svc/productads/suggestions/keywords/autocomplete"
REQUEST_BATCH_SIZE = 50      # Количество запросов в одной пачке
MIN_SLEEP_SECONDS = 15       # Минимальное время паузы в секундах
MAX_SLEEP_SECONDS = 60       # Максимальное время паузы в секундах
MAX_RETRIES = 6              # Максимальное количество повторных попыток для одного запроса
INITIAL_RETRY_DELAY = 5      # Начальная задержка перед повтором в секундах

# Определяем пути к файлам относительно директории скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
CURL_FILE = os.path.join(script_dir, "curl_headers.txt")
QUERIES_FILE = os.path.join(script_dir, "queries.txt")
DONE_FILE = os.path.join(script_dir, "queries_done.txt")
CSV_FILE = os.path.join(script_dir, "results.csv")
FAILED_FILE = os.path.join(script_dir, "queries_failed.txt") # Файл для неудачных запросов
# ---------------------


def parse_curl_headers_from_file(filepath):
    """Читает файл с cURL запросом и извлекает заголовки."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            curl_command = f.read()
            clean_command = curl_command.replace('^', '').replace('\\\n', ' ').replace('\n', ' ')

        args = shlex.split(clean_command)
        headers = {}
        iterator = iter(args)
        for arg in iterator:
            if arg == '-H':
                header_value = next(iterator, None)
                if header_value:
                    key, value = header_value.split(':', 1)
                    headers[key.strip()] = value.strip()
            elif arg in ('-b', '--cookie'):
                cookie_value = next(iterator, None)
                if cookie_value:
                    headers['cookie'] = cookie_value.strip()

        if not headers:
            print(f"Ошибка: Не удалось найти заголовки в файле '{filepath}'.")
            return None
        
        if 'user-agent' not in (k.lower() for k in headers):
            headers['user-agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        return headers
    except FileNotFoundError:
        print(f"Ошибка: Файл с хедерами '{filepath}' не найден.")
        return None
    except Exception as e:
        print(f"Произошла ошибка при парсинге файла с хедерами: {e}")
        return None

def load_queries():
    if not os.path.exists(QUERIES_FILE): return []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        return [q.strip() for q in f.readlines() if q.strip()]

def save_queries(queries):
    with open(QUERIES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(queries))

def append_done(query):
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(query + "\n")

def append_to_failed(query):
    """Записывает запрос, который не удалось обработать, в отдельный файл."""
    with open(FAILED_FILE, "a", encoding="utf-8") as f:
        f.write(query + "\n")

def save_to_csv(results):
    """Записывает данные в CSV с обработкой ошибки доступа к файлу."""
    if not results or not isinstance(results, list): return True
    
    # Пытаемся записать 3 раза с небольшой задержкой
    for attempt in range(3):
        try:
            file_exists = os.path.exists(CSV_FILE)
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerows(results)
            return True # Успех
        except PermissionError:
            print(f"!!! Ошибка доступа к файлу '{CSV_FILE}'. Возможно, он открыт в Excel.")
            if attempt < 2:
                print("--- Попробую снова через 3 секунды... ---")
                time.sleep(3)
            else:
                print("!!! Не удалось записать в файл. Пожалуйста, закройте его.")
                return False # Провал после всех попыток
        except Exception as e:
            print(f"!!! Произошла непредвиденная ошибка при записи в CSV: {e}")
            return False
            
    return False

def process_query(query, headers):
    """
    Отправляет запрос с автоматическими повторными попытками при неудаче.
    Возвращает True в случае успеха, False - если все попытки провалились.
    """
    payload = {"keyword": query, "sortBySearchVolume": False}
    retries = 0
    delay = INITIAL_RETRY_DELAY

    while retries < MAX_RETRIES:
        try:
            r = requests.post(URL, headers=headers, data=json.dumps(payload), timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # <<< ИЗМЕНЕНИЕ ЗДЕСЬ >>>
            # Проверяем, удалось ли сохранить результат
            if save_to_csv(data):
                return True # Успех, выходим из функции
            else:
                # Если сохранить не удалось, считаем это ошибкой и уходим на повтор
                raise IOError("Не удалось сохранить данные в CSV, файл заблокирован.")

        except (requests.exceptions.RequestException, json.JSONDecodeError, IOError) as e:
            retries += 1
            print(f"!!! Ошибка для '{query}': {str(e)[:150]}. Попытка {retries}/{MAX_RETRIES}...")
            if retries < MAX_RETRIES:
                print(f"--- Пауза на {delay} секунд перед повторной попыткой... ---")
                time.sleep(delay)
                delay *= 2  # Удваиваем задержку для следующей попытки
            else:
                print(f"!!! Превышен лимит попыток для '{query}'. Запрос будет пропущен.")
    
    return False # Если цикл завершился, значит все попытки провалились

def main():
    print("--- Запуск скрипта ---")
    
    headers = parse_curl_headers_from_file(CURL_FILE)
    if not headers:
        print("\nОстановка. Не удалось загрузить хедеры.")
        if not os.path.exists(CURL_FILE):
             open(CURL_FILE, 'w').close()
             print(f"Создан пустой файл '{CURL_FILE}'. Вставьте в него ваш cURL запрос.")
        return
    print("Хедеры успешно загружены.")
    
    if not os.path.exists(QUERIES_FILE) or os.path.getsize(QUERIES_FILE) == 0:
        print(f"\nФайл '{QUERIES_FILE}' пуст. Добавьте запросы.")
        if not os.path.exists(QUERIES_FILE): open(QUERIES_FILE, 'w').close()
        return
        
    queries = load_queries()
    if not queries:
        print("Нет запросов для обработки.")
        return
        
    print(f"Найдено {len(queries)} запросов для обработки.")

    request_counter = 0
    while queries:
        query = queries.pop(0)
        print(f"Обрабатываю: {query} (Запрос {request_counter + 1}/{REQUEST_BATCH_SIZE} в пачке, осталось {len(queries)})")
        
        if process_query(query, headers):
            # Успех
            save_queries(queries)
            append_done(query)
            request_counter += 1
            
            if request_counter >= REQUEST_BATCH_SIZE and queries:
                sleep_duration = random.uniform(MIN_SLEEP_SECONDS, MAX_SLEEP_SECONDS)
                print(f"\n--- Достигнут лимит в {REQUEST_BATCH_SIZE} запросов. Пауза на {sleep_duration:.2f} секунд... ---")
                time.sleep(sleep_duration)
                request_counter = 0
                print("--- Возобновляю работу ---\n")
        else:
            # Провал после всех попыток
            print(f"!!! Не удалось обработать запрос '{query}'. Записываю в файл ошибок и продолжаю.")
            append_to_failed(query)
            save_queries(queries) # Сохраняем, чтобы удалить "битый" запрос из списка
            
    print("\n--- Все запросы в списке обработаны. Работа скрипта завершена. ---")

if __name__ == "__main__":
    main()