#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест новой пошаговой логики завершения тренировки
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Добавляем текущую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Импортируем функции из основного бота
try:
    from lingualeo_pyth.tg_bot import calculate_next_repetition
except ImportError:
    # Fallback для прямого запуска
    def calculate_next_repetition(repeat_at, repeat_interval):
        """Рассчитывает следующий интервал повторения"""
        import datetime

        if not repeat_at or repeat_at == "0000-00-00 00:00:00+00":
            # Используем repeat_interval для расчета
            try:
                minutes = int(float(repeat_interval or 480))
                if minutes >= 1440:  # 24 часа
                    days = minutes // 1440
                    return f"↑ {days} д."
                elif minutes >= 480:  # 8 часов
                    hours = minutes // 60
                    return f"↓ {hours} ч."
                else:
                    return "↓ 6 ч."
            except (ValueError, TypeError):
                return "↓ 8 ч."
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
                    return "↓ 6 ч."

                days = time_diff.days
                hours = time_diff.seconds // 3600

                if days >= 1:
                    return f"↑ {days} д."
                elif hours >= 1:
                    return f"↓ {hours} ч."
                else:
                    return "↓ 6 ч."

            except Exception:
                return "↓ 8 ч."

def test_new_logic():
    """Тестируем новую логику расчета интервалов"""
    print("TESTIROVANIE NOVOY POSHAGOVOY LOGIKI")
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
        {"word_id": 64753, "word_value": "blandest", "correct_translate_value": "добродушный"},
        {"word_id": 12345, "word_value": "example", "correct_translate_value": "пример"},
        {"word_id": 67890, "word_value": "test", "correct_translate_value": "тест"}
    ]

    print("REZULTATY RASCHETA INTERVALOV:")
    print("-" * 40)

    for word in training_words:
        word_id = str(word.get('word_id', ''))
        word_value = word.get('word_value', 'neizvestnoe slovo')
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
            print(f"• {word_value} — {translate_value}: {interval_text}")
        else:
            print(f"• {word_value} — {translate_value}: dannye ne naydeny")

    print("\n" + "=" * 50)
    print("TESTIROVANIE ZAVERSHENO")
    print("\nOZHiDAEMYY PROTSESS:")
    print("1. Trenirovka zavreshena")
    print("2. Polzovatel podtverzhdaet OK")
    print("3. Pokazyvaetsya zapros dlya otpravki")
    print("4. Polzovatel podtverzhdaet otpravku")
    print("5. Pokazyvaetsya otvet servera")
    print("6. Polzovatel podtverzhdaet obrabotku")
    print("7. Pokazyvayutsya intervaly povtoreniya")
    print("8. Pokazyvaetsya finalnaya statistika")

if __name__ == "__main__":
    test_new_logic()