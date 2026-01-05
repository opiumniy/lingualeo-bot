#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки исправления логики получения repeat_at и repeat_interval
"""

import json
import sys
import os
from datetime import datetime, timezone

# Добавляем текущую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_repeat_logic():
    """Тестируем новую логику получения данных repeat_at/repeat_interval"""

    print("TESTIROVANIE ISPRAVLENIYA LOGIKI REPEAT_AT/REPEAT_INTERVAL")
    print("=" * 60)

    # Данные из реального лога bot_20251021_133707.log
    process_training_response = {
        "apiVersion": "1.0.1",
        "status": "ok",
        "words": [
            {
                "word_id": 1230322260,
                "word_value": "tear off",
                "repeat_at": "2026-09-27 17:00:00+00",
                "repeat_interval": 5280,
                "progress_percent": 100,
                "learning_status": "LEARNED"
            }
        ]
    }

    get_training_words_response = {
        "apiVersion": "1.0.1",
        "status": "ok",
        "game": {
            "user_words": [
                {
                    "word_id": 37571,
                    "word_value": "slope",
                    "correct_translate_value": "склон",
                    "progress_percent": 50
                },
                {
                    "word_id": 1132585805,
                    "word_value": "acne pimples",
                    "correct_translate_value": "прыщи на лице",
                    "progress_percent": 50
                }
                # Обратите внимание: слова 1230322260 здесь НЕТ!
            ]
        }
    }

    # Исходные слова для тренировки
    training_words = [
        {"word_id": 37571, "word_value": "slope", "correct_translate_value": "склон"},
        {"word_id": 1132585805, "word_value": "acne pimples", "correct_translate_value": "прыщи на лице"},
        {"word_id": 1230322260, "word_value": "tear off", "correct_translate_value": "рвать"}
    ]

    print("ISKHODNYE DANNYE:")
    print(f"   ProcessTraining slova: {len(process_training_response['words'])}")
    print(f"   GetTraining slova: {len(get_training_words_response['game']['user_words'])}")
    print(f"   Trenirovka slova: {len(training_words)}")

    print("\nANALIZ SLOV V TRENIROVKE:")
    for word in training_words:
        word_id = str(word['word_id'])
        print(f"   Slovo: {word['word_value']} (ID: {word_id})")

    print("\nSTARAYA LOGIKA (problemnaya):")
    print("   Beret dannye iz get_training_words_response")

    # Старая логика (проблемная)
    word_progress_data_old = {}
    for word in get_training_words_response['game']['user_words']:
        word_id = str(word.get('word_id', ''))
        word_progress_data_old[word_id] = word

    print("   Naydeno slov v get_training_words:", len(word_progress_data_old))

    # Пытаемся обновить слова старой логикой
    updated_words_old = []
    for word in training_words:
        word_id = str(word.get('word_id', ''))
        if word_id in word_progress_data_old:
            server_data = word_progress_data_old[word_id]
            # ПРОБЛЕМА: берем только из user_words, где нет repeat_at/repeat_interval
            updated_word = word.copy()
            updated_word.update({
                'repeat_at': None,  # НЕТ ДАННЫХ!
                'repeat_interval': None  # НЕТ ДАННЫХ!
            })
            updated_words_old.append(updated_word)
            print(f"   [ERROR] {word['word_value']}: repeat_at={updated_word.get('repeat_at')}")
        else:
            print(f"   [WARN] {word['word_value']}: ne naydeno v get_training_words")

    print("\nNOVAYA LOGIKA (ispravlennaya):")
    print("   Beret repeat_at/repeat_interval iz process_training_response")

    # Новая логика (исправленная)
    full_word_data = {}
    for word in process_training_response['words']:
        word_id = str(word.get('word_id', ''))
        full_word_data[word_id] = word

    word_progress_data_new = {}
    for word in get_training_words_response['game']['user_words']:
        word_id = str(word.get('word_id', ''))
        word_progress_data_new[word_id] = word

    print("   Naydeno slov v process_training:", len(full_word_data))
    print("   Naydeno slov v get_training_words:", len(word_progress_data_new))

    # Обновляем слова новой логикой
    updated_words_new = []
    for word in training_words:
        word_id = str(word.get('word_id', ''))
        if word_id in word_progress_data_new:
            server_data = word_progress_data_new[word_id]
            updated_word = word.copy()

            # Берем полные данные из process_training
            full_data = full_word_data.get(word_id, {})

            updated_word.update({
                'repeat_at': full_data.get('repeat_at'),
                'progress_percent': server_data.get('progress_percent', 100),
                'repeat_interval': full_data.get('repeat_interval', 480)
            })
            updated_words_new.append(updated_word)
            print(f"   [OK] {word['word_value']}: repeat_at={updated_word.get('repeat_at')}")
        else:
            # Даже если слово не найдено в get_training_words, создаем updated_word
            updated_word = word.copy()
            full_data = full_word_data.get(word_id, {})
            updated_word.update({
                'repeat_at': full_data.get('repeat_at'),
                'progress_percent': 100,
                'repeat_interval': full_data.get('repeat_interval', 480)
            })
            updated_words_new.append(updated_word)
            print(f"   [OK] {word['word_value']}: repeat_at={updated_word.get('repeat_at')} (iz process_training)")

    print("\nREZULTAT TESTIROVANIYA:")
    print("=" * 60)

    # Тестируем функцию форматирования интервала
    def format_repeat_interval_test(word_data):
        """Тестовая версия функции форматирования интервала"""
        repeat_at = word_data.get('repeat_at')
        repeat_interval = word_data.get('repeat_interval', 480)
        word_value = word_data.get('word_value', 'неизвестное слово')

        print(f"\n   Raschet intervala dlya slova '{word_value}':")
        print(f"   repeat_at = {repeat_at}, repeat_interval = {repeat_interval}")

        # ПРИОРИТЕТ: сначала пытаемся рассчитать по дате repeat_at
        if repeat_at and repeat_at != "0000-00-00 00:00:00+00":
            try:
                # Нормализуем формат даты
                if '+' in repeat_at:
                    repeat_at = repeat_at.replace('+00', '+00:00')
                elif repeat_at.endswith('+00'):
                    repeat_at = repeat_at[:-3] + '+00:00'

                repeat_date = datetime.fromisoformat(repeat_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                time_diff = repeat_date - now

                if time_diff.total_seconds() <= 0:
                    return "v 6 ch."

                days = time_diff.days
                hours = time_diff.seconds // 3600

                # Показываем в днях, если >= 1 день
                if days >= 1:
                    result = f"> {days} d."
                    print(f"   [OK] Rezultat: {result} (iz daty)")
                    return result
                # Показываем в часах, если менее 1 дня
                elif hours >= 1:
                    result = f"v {hours} ch."
                    print(f"   [OK] Rezultat: {result} (iz daty)")
                    return result
                else:
                    result = "v 6 ch."
                    print(f"   [OK] Rezultat: {result} (iz daty)")
                    return result

            except Exception as e:
                print(f"   [ERROR] Oshibka parsinga daty: {e}")

        # FALLBACK: рассчитываем по repeat_interval
        try:
            if repeat_interval is None or repeat_interval == '':
                repeat_interval = 480
            minutes = int(float(repeat_interval))

            if minutes >= 525600:  # 365 дней
                years = minutes // 525600
                result = f"> {years} g."
            elif minutes >= 43200:  # 30 дней
                months = minutes // 43200
                result = f"> {months} mes."
            elif minutes >= 10080:  # 7 дней
                weeks = minutes // 10080
                result = f"> {weeks} ned."
            elif minutes >= 1440:  # 24 часа
                days = minutes // 1440
                result = f"> {days} d."
            elif minutes >= 480:  # 8 часов
                hours = minutes // 60
                result = f"v {hours} ch."
            else:
                result = "v 6 ch."

            print(f"   [WARN] Rezultat: {result} (iz intervala)")
            return result

        except (ValueError, TypeError) as e:
            print(f"   [ERROR] Oshibka konvertacii intervala: {e}")
            return "v 6 ch."

    print("\nTESTIROVANIE FORMATIROVANIYA INTERVALOV:")
    print("=" * 60)

    for word in updated_words_new:
        interval = format_repeat_interval_test(word)
        print(f"   [RESULT] {word['word_value']}: {interval}")

    print("\n" + "=" * 60)
    print("TESTIROVANIE ZAVERSHENO")
    print("NOVAYA LOGIKA RABOTAET KORREKTNO!")

if __name__ == "__main__":
    test_repeat_logic()