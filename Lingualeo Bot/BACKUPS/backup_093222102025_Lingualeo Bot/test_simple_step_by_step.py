#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест новой логики расчета интервалов
"""

import sys
import os
import json
from datetime import datetime, timedelta

def calculate_next_repetition(repeat_at, repeat_interval):
    """Рассчитывает следующий интервал повторения"""
    import datetime

    if not repeat_at or repeat_at == "0000-00-00 00:00:00+00":
        # Используем repeat_interval для расчета
        try:
            minutes = int(float(repeat_interval or 480))
            if minutes >= 1440:  # 24 часа
                days = minutes // 1440
                return f"+ {days} d."
            elif minutes >= 480:  # 8 часов
                hours = minutes // 60
                return f"- {hours} ch."
            else:
                return "- 6 ch."
        except (ValueError, TypeError):
            return "- 8 ch."
    else:
        # Рассчитываем по дате
        try:
            if '+' in repeat_at:
                repeat_at = repeat_at.replace('+00', '+00:00')
            elif repeat_at.endswith('+00'):
                repeat_at = repeat_at[:-3] + '+00:00'

            repeat_date = datetime.datetime.fromisoformat(repeat_at.replace('Z', '+00:00'))
            now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            time_diff = repeat_date - now

            if time_diff.total_seconds() <= 0:
                return "- 6 ch."

            days = time_diff.days
            hours = time_diff.seconds // 3600

            if days >= 1:
                return f"+ {days} d."
            elif hours >= 1:
                return f"- {hours} ch."
            else:
                return "- 6 ch."

        except Exception:
            return "- 8 ch."

def test_new_logic():
    """Тестируем новую логику расчета интервалов"""
    print("TEST NEW STEP-BY-STEP LOGIC")
    print("=" * 50)

    # Тестовые данные - эмуляция ответа сервера
    mock_server_response = {
        "status": "ok",
        "words": [
            {
                "word_id": 64753,
                "word_value": "blandest",
                "repeat_at": "2025-10-21 19:00:00+00",
                "repeat_interval": 480,
                "progress_percent": 100
            },
            {
                "word_id": 12345,
                "word_value": "example",
                "repeat_at": "2025-10-25 10:00:00+00",
                "repeat_interval": 5280,
                "progress_percent": 100
            },
            {
                "word_id": 67890,
                "word_value": "test",
                "repeat_at": "0000-00-00 00:00:00+00",
                "repeat_interval": 480,
                "progress_percent": 50
            }
        ]
    }

    # Тестовые слова тренировки
    training_words = [
        {"word_id": 64753, "word_value": "blandest", "correct_translate_value": "dobroduynyy"},
        {"word_id": 12345, "word_value": "example", "correct_translate_value": "primer"},
        {"word_id": 67890, "word_value": "test", "correct_translate_value": "test"}
    ]

    print("INTERVAL CALCULATION RESULTS:")
    print("-" * 40)

    for word in training_words:
        word_id = str(word.get('word_id', ''))
        word_value = word.get('word_value', 'unknown word')
        translate_value = word.get('correct_translate_value', '')

        # Ищем данные слова в ответе сервера
        server_word_data = None
        for server_word in mock_server_response['words']:
            if str(server_word.get('word_id', '')) == word_id:
                server_word_data = server_word
                break

        if server_word_data:
            repeat_at = server_word_data.get('repeat_at', '')
            repeat_interval = server_word_data.get('repeat_interval', 480)

            # Рассчитываем интервал
            interval_text = calculate_next_repetition(repeat_at, repeat_interval)
            print(f"* {word_value} - {translate_value}: {interval_text}")
        else:
            print(f"* {word_value} - {translate_value}: data not found")

    print("\n" + "=" * 50)
    print("TESTING COMPLETED")
    print("\nEXPECTED PROCESS:")
    print("1. Training completed")
    print("2. User confirms OK")
    print("3. Request for sending is shown")
    print("4. User confirms sending")
    print("5. Server response is shown")
    print("6. User confirms processing")
    print("7. Repetition intervals are shown")
    print("8. Final statistics are shown")

if __name__ == "__main__":
    test_new_logic()