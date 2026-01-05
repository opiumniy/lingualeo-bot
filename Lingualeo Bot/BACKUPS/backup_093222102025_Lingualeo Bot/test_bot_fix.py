#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testovyy skript dlya emulyacii raboty ispravlennogo bota
Baziruetsya na realnykh dannykh iz loga bot_20251021_133707.log
"""

import json
import sys
import os
from datetime import datetime, timezone

def test_bot_with_real_data():
    """Emuliruem rabotu ispravlennogo bota s realnymi dannymi iz loga"""

    print("EMULYACIYA RABOTY ISPRAVLENNOGO BOTA")
    print("=" * 50)

    # РЕАЛЬНЫЕ ДАННЫЕ ИЗ ЛОГА bot_20251021_133707.log

    # Ответ ProcessTraining сервера (где есть repeat_at и repeat_interval)
    process_training_response = {
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

    # Эмулируем ответ от export_all_words (словарь пользователя с полными данными)
    user_dictionary_response = [
        {
            "word_id": 37571,
            "word_value": "slope",
            "user_translates": "склон",
            "progress_percent": 50,
            "repeat_at": None,
            "repeat_interval": 480
        },
        {
            "word_id": 1132585805,
            "word_value": "acne pimples",
            "user_translates": "прыщи на лице",
            "progress_percent": 50,
            "repeat_at": None,
            "repeat_interval": 480
        },
        {
            "word_id": 1230322260,
            "word_value": "tear off",
            "user_translates": "рвать",
            "progress_percent": 100,
            "repeat_at": "2026-09-27 17:00:00+00",
            "repeat_interval": 5280
        }
    ]

    # Ответ get_training_words сервера (где НЕТ repeat_at и repeat_interval)
    get_training_words_response = {
        "status": "ok",
        "game": {
            "user_words": [
                {
                    "word_id": 37571,
                    "word_value": "slope",
                    "correct_translate_value": "sklon",
                    "progress_percent": 50
                },
                {
                    "word_id": 1132585805,
                    "word_value": "acne pimples",
                    "correct_translate_value": "pryschi na lice",
                    "progress_percent": 50
                }
                # Обратите внимание: слова 1230322260 здесь НЕТ!
            ]
        }
    }

    # Исходные слова для тренировки
    training_words = [
        {"word_id": 37571, "word_value": "slope", "correct_translate_value": "sklon"},
        {"word_id": 1132585805, "word_value": "acne pimples", "correct_translate_value": "pryschi na lice"},
        {"word_id": 1230322260, "word_value": "tear off", "correct_translate_value": "rvat"}
    ]

    print("ISKHODNYE DANNYE IZ LOGA:")
    print(f"   ProcessTraining slova: {len(process_training_response['words'])}")
    print(f"   GetTraining slova: {len(get_training_words_response['game']['user_words'])}")
    print(f"   Trenirovka slova: {len(training_words)}")

    print("\nSLOVA V TRENIROVKE:")
    for word in training_words:
        print(f"   {word['word_value']} (ID: {word['word_id']})")

    # EMULYACIYA ISPRAVLENNOY LOGIKI BOTA

    print("\nISPRAVLENNAYA LOGIKA BOTA:")
    print("-" * 30)

    # Создаем словари данных (как в исправленном боте)
    full_word_data = {}
    # Данные repeat_at/repeat_interval берем из словаря пользователя (эмулируем export_all_words)
    for word in user_dictionary_response:
        word_id = str(word.get('word_id', ''))
        full_word_data[word_id] = word

    word_progress_data = {}
    for word in get_training_words_response['game']['user_words']:
        word_id = str(word.get('word_id', ''))
        word_progress_data[word_id] = word

    print(f"   Naydeno v ProcessTraining: {len(full_word_data)} slov")
    print(f"   Naydeno v GetTraining: {len(word_progress_data)} slov")

    # Obnovlyaem slova (kak v ispravlennom bote)
    updated_words = []
    for word in training_words:
        word_id = str(word.get('word_id', ''))
        if word_id in word_progress_data:
            server_data = word_progress_data[word_id]
            updated_word = word.copy()

            # Berem polnye dannye iz process_training (ISPRAVLENIE!)
            full_data = full_word_data.get(word_id, {})

            updated_word.update({
                'repeat_at': full_data.get('repeat_at'),
                'progress_percent': server_data.get('progress_percent', 100),
                'repeat_interval': full_data.get('repeat_interval', 480)
            })
            updated_words.append(updated_word)
            print(f"   [OK] {word['word_value']}: repeat_at={updated_word.get('repeat_at')}")
        else:
            # Dazhe esli slovo ne naydeno v get_training_words, sozdaem updated_word
            updated_word = word.copy()
            full_data = full_word_data.get(word_id, {})
            updated_word.update({
                'repeat_at': full_data.get('repeat_at'),
                'progress_percent': 100,
                'repeat_interval': full_data.get('repeat_interval', 480)
            })
            updated_words.append(updated_word)
            print(f"   [OK] {word['word_value']}: repeat_at={updated_word.get('repeat_at')} (iz ProcessTraining)")

    # Opredelyaem kategorii slov (kak v ispravlennom bote)
    studying_words = [word for word in updated_words if not word.get('repeat_at') or word.get('repeat_at') == "0000-00-00 00:00:00+00"]
    remembered_words = [word for word in updated_words if word.get('repeat_at') and word.get('repeat_at') != "0000-00-00 00:00:00+00"]

    print(f"\n   Na izuchenii: {len(studying_words)} slov")
    print(f"   Pomnyu: {len(remembered_words)} slov")

    # Функция форматирования интервала (из исправленного бота)
    def format_repeat_interval(word_data):
        repeat_at = word_data.get('repeat_at')
        repeat_interval = word_data.get('repeat_interval', 480)
        word_value = word_data.get('word_value', 'neizvestnoe slovo')

        print(f"\n   Raschet dlya '{word_value}': repeat_at={repeat_at}, repeat_interval={repeat_interval}")

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
                    print(f"   [OK] Rezultat: {result} (IZ DATY)")
                    return result
                # Показываем в часах, если менее 1 дня
                elif hours >= 1:
                    result = f"v {hours} ch."
                    print(f"   [OK] Rezultat: {result} (IZ DATY)")
                    return result
                else:
                    result = "v 6 ch."
                    print(f"   [OK] Rezultat: {result} (IZ DATY)")
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

            print(f"   [WARN] Rezultat: {result} (IZ INTERVALA)")
            return result

        except (ValueError, TypeError) as e:
            print(f"   [ERROR] Oshibka konvertacii: {e}")
            return "v 6 ch."

    print("\nFORMATIROVANIE INTERVALOV:")
    print("-" * 30)

    # Pokazyvaem rezul'taty dlya vsekh slov
    for word in updated_words:
        interval = format_repeat_interval(word)
        print(f"   [RESULT] {word['word_value']}: {interval}")

    print("\n" + "=" * 50)
    print("EMULYACIYA ZAVERSHENA")
    print("ISPRAVLENNYY BOT BUDET RABOTAT TAK:")
    print()
    print("IZUCHENIE:")
    for word in studying_words:
        interval = format_repeat_interval(word)
        translate = word.get('correct_translate_value', 'unknown')
        print(f"   {word['word_value']} -> {translate}: {interval}")

    print()
    print("POMNYU:")
    for word in remembered_words:
        interval = format_repeat_interval(word)
        translate = word.get('correct_translate_value', 'unknown')
        print(f"   {word['word_value']} -> {translate}: {interval}")

if __name__ == "__main__":
    test_bot_with_real_data()