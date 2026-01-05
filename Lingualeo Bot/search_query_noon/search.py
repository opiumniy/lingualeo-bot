import requests
import csv
import json
import os
import time # Импортируем модуль для управления временем

# --- КОНФИГУРАЦИЯ ---
URL = "https://admanager.noon.partners/_svc/productads/suggestions/keywords/autocomplete"
REQUEST_DELAY_SECONDS = 5 # Задержка между запросами в секундах

# Заголовки теперь БЕЗ cookie. Он будет добавлен позже из файла.
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "access-control-allow-origin": "*",
    "baggage": "sentry-environment=production,sentry-release=604b705d9aaa8f525d132634d3316c2e11d8d068,sentry-public_key=838de52b3cc5250a5601d84173a85cc6,sentry-trace_id=52a46d303c24407890ca8e4c2fea9d44,sentry-sample_rate=1,sentry-transaction=%2Fcampaign%2Fv2,sentry-sampled=true",
    "cache-control": "no-cache, max-age=0, must-revalidate, no-store",
    "content-type": "application/json",
    "origin": "https://admanager.noon.partners",
    "priority": "u=1, i",
    "referer": "https://admanager.noon.partners/en-ae/campaign/v2",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sentry-trace": "52a46d303c24407890ca8e4c2fea9d44-82660dfd92796249-1",
    "timeout": "300000",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "x-advertiser-codes": "ADV_509186C54A39",
    "x-border-enabled": "true",
    "x-cms": "v3",
    "x-content": "desktop",
    "x-locale": "en-ae",
    "x-mp": "noon",
    "x-platform": "web",
    "x-project": "null",
    "x-seller-view": "true"
}

# --- ПУТИ К ФАЙЛАМ ---
script_dir = os.path.dirname(os.path.abspath(__file__))
QUERIES_FILE = os.path.join(script_dir, "queries.txt")
DONE_FILE = os.path.join(script_dir, "queries_done.txt")
CSV_FILE = os.path.join(script_dir, "results.csv")
COOKIE_FILE = os.path.join(script_dir, "cookies.txt") # Путь к новому файлу

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ COOKIE ---
def load_cookie():
    """Читает cookie из файла cookies.txt."""
    if not os.path.exists(COOKIE_FILE):
        print(f"ОШИБКА: Файл '{COOKIE_FILE}' не найден.")
        print("Пожалуйста, создайте этот файл и вставьте в него вашу строку cookie.")
        return None
    
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookie_string = f.read().strip()
    
    if not cookie_string:
        print(f"ОШИБКА: Файл '{COOKIE_FILE}' пуст.")
        print("Пожалуйста, вставьте в него вашу строку cookie.")
        return None
        
    return cookie_string

# --- СУЩЕСТВУЮЩИЕ ФУНКЦИИ (без изменений) ---
def load_queries():
    if not os.path.exists(QUERIES_FILE):
        return []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        return [q.strip() for q in f.readlines() if q.strip()]

def save_queries(queries):
    with open(QUERIES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(queries))

def append_done(query):
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(query + "\n")

def save_to_csv(results):
    if not results or not isinstance(results, list):
        print("Нет данных для сохранения в CSV.")
        return
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

def process_query(query):
    payload = {"keyword": query, "sortBySearchVolume": False}
    try:
        r = requests.post(URL, headers=HEADERS, data=json.dumps(payload), timeout=15)
        r.raise_for_status()
        try:
            data = r.json()
            if data:
                save_to_csv(data)
            return True
        except json.JSONDecodeError:
            print(f"Ошибка для '{query}': Не удалось декодировать JSON.")
            print(f"Статус-код: {r.status_code}")
            print(f"Ответ сервера (первые 500 символов): {r.text[:500]}")
            return False
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка HTTP для '{query}': {e}")
        print(f"Ответ сервера (первые 500 символов): {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"Общая ошибка для '{query}': {e}")
        return False

# --- ОСНОВНАЯ ФУНКЦИЯ (ИЗМЕНЕНА) ---
def main():
    # 1. Загружаем cookie. Если не получилось, выходим.
    cookie_string = load_cookie()
    if not cookie_string:
        return
    HEADERS['cookie'] = cookie_string

    # 2. Проверяем файл с запросами
    if not os.path.exists(QUERIES_FILE) or os.path.getsize(QUERIES_FILE) == 0:
        print(f"Файл '{QUERIES_FILE}' не найден или пуст. Добавьте в него запросы.")
        if not os.path.exists(QUERIES_FILE):
            open(QUERIES_FILE, 'w').close()
        return
        
    queries = load_queries()
    if not queries:
        print("Нет запросов для обработки в queries.txt")
        return

    # 3. Запускаем цикл обработки с задержкой
    total_queries = len(queries)
    for index, query in enumerate(queries.copy()):
        print(f"--- Обрабатываю: '{query}' ({index + 1} из {total_queries}) ---")
        
        if process_query(query):
            queries.remove(query)
            save_queries(queries)
            append_done(query)
        else:
            print("\nОстановка скрипта из-за ошибки. Вероятно, нужно обновить cookie в файле cookies.txt.")
            break 

        # Ждем перед следующим запросом, если это не последний элемент
        if index < total_queries - 1:
            print(f"Пауза {REQUEST_DELAY_SECONDS} секунд...")
            time.sleep(REQUEST_DELAY_SECONDS)

    print("\nРабота завершена.")


if __name__ == "__main__":
    main()