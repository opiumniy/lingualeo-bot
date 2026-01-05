import pandas as pd
import os
import sys
import difflib
import random
from datetime import datetime, timedelta

# Fix import path for local utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ensure_requirements

sys.stdout.reconfigure(encoding='utf-8')

ensure_requirements()

# --- Константы ---
VOCABULARY_FILE = "vocabulary.csv"
STATS_FILE = "training_stats.csv"

def run_training_session(mode='free'):
    """
    Загружает словарь и запускает простую тренировку из 10 слов.
    """
    # --- Шаг 1: Загрузка данных ---
    if not os.path.exists(VOCABULARY_FILE):
        print(f"ОШИБКА: Файл словаря '{VOCABULARY_FILE}' не найден.")
        print("Сначала запусти скрипт 'lingualeo_ultimate_parser.py', чтобы его создать.")
        return

    try:
        df = pd.read_csv(VOCABULARY_FILE)
        print(f"Словарь успешно загружен. Всего слов: {len(df)}")
        # Исправляем типы для избежания warning
        df['interval_hours'] = df['interval_hours'].astype(float)
        df['ease_factor'] = df['ease_factor'].astype(float)
    except Exception as e:
        print(f"Не удалось прочитать файл словаря: {e}")
        return

    # Конвертируем next_repetition_date в datetime
    df['next_repetition_date'] = pd.to_datetime(df['next_repetition_date'])

    # --- Шаг 2: Выбор слов для тренировки с интервальным повторением ---
    now = datetime.now()
    # Выбираем слова, готовые к повторению
    due_words = df[df['next_repetition_date'] <= now]
    print(f"Слов, готовых к повторению: {len(due_words)}")

    if len(due_words) >= 10:
        training_df = due_words.sample(n=10)
    elif len(due_words) > 0:
        # Добавляем оставшиеся случайные слова
        remaining = 10 - len(due_words)
        other_words = df[df['next_repetition_date'] > now].sample(n=remaining)
        training_df = pd.concat([due_words, other_words])
    else:
        # Если нет готовых, берем случайные
        if len(df) < 10:
            training_df = df
        else:
            training_df = df.sample(n=10)
    
    print("\n--- Начинаем тренировку! ---")
    print("Я покажу тебе русское слово, а ты введи перевод на английском.")
    
    correct_answers = 0
    total_questions = len(training_df)

    # Сохраняем индексы для обновления df
    original_indices = training_df.index.tolist()

    # --- Шаг 3: Цикл тренировки ---
    for index, row in training_df.iterrows():
        russian_word = row['russian']
        english_word = row['english']
        
        if mode == 'multiple':
            # Генерируем 3 неправильных варианта
            distractors = df[df['english'] != english_word]['english'].sample(n=3).tolist()
            options = distractors + [english_word]
            import random
            random.shuffle(options)
            correct_letter = chr(65 + options.index(english_word))  # A, B, C, D
            
            print(f"\nРусский: {russian_word}")
            for i, opt in enumerate(options):
                print(f"{chr(65 + i)}. {opt}")
            
            user_choice = input("Выберите вариант (A/B/C/D или 1/2/3/4): ").strip().upper()
            # Поддержка числового ввода
            if user_choice.isdigit() and 1 <= int(user_choice) <= 4:
                user_choice = chr(64 + int(user_choice))  # 1->A, 2->B, etc.
            
            is_correct = user_choice == correct_letter
            if is_correct:
                print(f"✅ Верно! ({correct_letter})")
            else:
                print(f"❌ Неверно. Правильный: {correct_letter} - {english_word}")
        else:  # free mode
            user_input = input(f"\nРусский: {russian_word}\nАнглийский: ")
            
            # Нормализация для множественных форм (простая: удаляем 's' или 'es' в конце)
            def normalize_word(word):
                word = word.strip().lower()
                if word.endswith('es'):
                    return word[:-2]
                if word.endswith('s'):
                    return word[:-1]
                return word

            user_norm = normalize_word(user_input)
            english_norm = normalize_word(english_word)

            # Fuzzy matching для опечаток
            similarity = difflib.SequenceMatcher(None, user_norm, english_norm).ratio()

            is_correct = similarity > 0.8 or user_norm == english_norm
            if is_correct:
                print("✅ Верно!")
            else:
                print(f"❌ Неверно. Правильный ответ: {english_word} (similarity: {similarity:.2f})")

        correct_answers += 1 if is_correct else 0

        # --- Шаг 4: Обновление интервала (общее для обоих режимов) ---
        if is_correct:
            df.loc[index, 'repetitions'] += 1
            repetitions = df.loc[index, 'repetitions']
            ease_factor = df.loc[index, 'ease_factor']
            # Упрощенная SM2: interval = repetitions * ease_factor
            new_interval = repetitions * ease_factor
            df.loc[index, 'interval_hours'] = new_interval
            # Следующая дата: + interval часов
            next_date = now + timedelta(hours=new_interval)
            df.loc[index, 'next_repetition_date'] = next_date
        else:
            # На неправильный: сброс repetitions=0, interval=12 часов
            df.loc[index, 'repetitions'] = 0
            df.loc[index, 'interval_hours'] = 12
            next_date = now + timedelta(hours=12)
            df.loc[index, 'next_repetition_date'] = next_date
            # Уменьшаем ease_factor
            df.loc[index, 'ease_factor'] = max(1.3, df.loc[index, 'ease_factor'] - 0.2)

    # Сохраняем обновленный df обратно в CSV
    df['next_repetition_date'] = df['next_repetition_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(VOCABULARY_FILE, index=False, encoding='utf-8-sig')
    print("Обновленный словарь с прогрессом сохранен.")

    # --- Сохранение статистики тренировки ---
    stats_file = "training_stats.csv"
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    stats_data = {
        'date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'correct': [correct_answers],
        'total': [total_questions],
        'accuracy': [f"{accuracy:.2f}%"],
        'due_words': [len(due_words)]
    }
    stats_df = pd.DataFrame(stats_data)
    
    if os.path.exists(stats_file):
        stats_df.to_csv(stats_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
    
    print(f"Статистика тренировки сохранена в {stats_file}")

    print("\n--- Тренировка окончена! ---")
    print(f"Твой результат: {correct_answers} из {total_questions} правильных ответов.")

def show_stats():
    """
    Показывает статистику последних тренировок.
    """
    if not os.path.exists(STATS_FILE):
        print(f"Файл статистики '{STATS_FILE}' не найден. Проведите хотя бы одну тренировку.")
        return

    try:
        stats_df = pd.read_csv(STATS_FILE)
        print("\n--- Статистика тренировок ---")
        if len(stats_df) > 0:
            # Показываем последние 5 записей
            print(stats_df.tail().to_string(index=False))
            # Общая статистика
            avg_accuracy = stats_df['accuracy'].str.rstrip('%').astype(float).mean()
            total_sessions = len(stats_df)
            print(f"\nОбщая статистика: {total_sessions} сессий, средняя точность: {avg_accuracy:.2f}%")
        else:
            print("Нет данных о тренировках.")
    except Exception as e:
        print(f"Ошибка при чтении статистики: {e}")

if __name__ == "__main__":
    while True:
        print("\n--- Меню Lingualeo Reverse Trainer ---")
        print("1. Тренировка: свободный ввод")
        print("2. Тренировка: множественный выбор (4 варианта)")
        print("3. Просмотреть статистику")
        print("4. Выход")
        
        choice = input("Выберите опцию (1-4): ").strip()
        
        if choice == '1':
            run_training_session(mode='free')
        elif choice == '2':
            run_training_session(mode='multiple')
        elif choice == '3':
            show_stats()
        elif choice == '4':
            print("До свидания!")
            break
        else:
            print("Неверный выбор. Попробуйте снова.")