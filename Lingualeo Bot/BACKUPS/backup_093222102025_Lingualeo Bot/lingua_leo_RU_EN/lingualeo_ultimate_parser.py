import json
import pandas as pd
from datetime import datetime
import os
import sys

# Fix import path for local utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ensure_requirements
from api_client import LingualeoAPIClient
from config import get_global_cookies_path

ensure_requirements()

# Константы
VOCABULARY_FILE = "vocabulary.csv"
RAW_RESPONSE_FILE = "raw_api_response.json"

def export_all_words():
    """
    Экспортирует все слова из Lingualeo с использованием API клиента.
    """
    print("--- Запуск экспортера слов ---")

    client = LingualeoAPIClient()
    if not client.load_cookies():
        print("Ошибка: Куки не найдены. Используйте глобальный файл куки.")
        return None

    try:
        words_list = client.export_all_words()
        if not words_list:
            print("ОШИБКА: Список слов пуст.")
            return None

        # Сохраняем сырой ответ
        with open(RAW_RESPONSE_FILE, 'w', encoding='utf-8') as f:
            # Для сохранения полного ответа, но поскольку export возвращает data, сохраним его
            json.dump({'data': words_list}, f, ensure_ascii=False, indent=4)
        print(f"Сырой JSON-ответ сохранен в {RAW_RESPONSE_FILE}")

        print(f"\n------ Успех! ------")
        print(f"Найдено {len(words_list)} слов.")
        return words_list

    except Exception as e:
        print(f"\nОшибка при экспорте: {e}")
        return None

def save_words_to_csv(words):
    """
    Сохраняет слова в CSV.
    """
    if not words:
        return

    processed_words = []
    for word_data in words:
        processed_words.append({
            'word_id': word_data.get('id'),
            'english': word_data.get('wd'),
            'russian': word_data.get('trc')
        })

    df = pd.DataFrame(processed_words)
    df.dropna(subset=['russian'], inplace=True)
    df = df[df['russian'] != '']
    df.drop_duplicates(subset=['word_id'], keep='first', inplace=True)

    # Поля для интервального повторения
    df['next_repetition_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df['interval_hours'] = 12
    df['ease_factor'] = 2.5
    df['repetitions'] = 0

    df.to_csv(VOCABULARY_FILE, index=False, encoding='utf-8-sig')
    print(f"\nСловарь на {len(df)} слов сохранен в {VOCABULARY_FILE}")

if __name__ == "__main__":
    if os.path.exists(VOCABULARY_FILE):
        os.remove(VOCABULARY_FILE)
    if os.path.exists(RAW_RESPONSE_FILE):
        os.remove(RAW_RESPONSE_FILE)
    
    all_my_words = export_all_words()
    if all_my_words:
        save_words_to_csv(all_my_words)