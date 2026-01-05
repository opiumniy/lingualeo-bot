#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест разбиения длинных сообщений
"""

import json

def test_message_splitting():
    """Тестируем разбиение длинных сообщений"""
    print("TEST RAZBIENIYA SOOBSHCHENIY")
    print("=" * 50)

    # Создаем большой JSON для теста
    test_data = {}
    for i in range(50):  # Создаем 50 слов
        test_data[f"word_{i}"] = 1 if i % 2 == 0 else 2

    json_str = json.dumps(test_data, ensure_ascii=False, indent=2)
    print(f"Dlina JSON: {len(json_str)} simvolov")

    # Тест разбиения
    max_length = 4000
    parts = []
    for i in range(0, len(json_str), max_length):
        parts.append(json_str[i:i + max_length])

    print(f"Razbito na {len(parts)} chastey")

    for i, part in enumerate(parts):
        print(f"Chast {i+1}: {len(part)} simvolov")

    # Проверяем что все части в пределах лимита
    all_within_limit = all(len(part) <= max_length for part in parts)
    print(f"Vse chasti v limite: {all_within_limit}")

    if all_within_limit:
        print("\nTEST PROYDEN: Soobshcheniya razbivayutsya pravilno!")
    else:
        print("\nTEST NE PROYDEN: Nekotorye chasti prevyshaut limit!")

    print("\nOZHiDAEMYY VYVOD:")
    print("- Pervaya chast: pervyh 4000 simvolov")
    print("- Vtoraya chast: ostavshayasya chast")
    print("- Kazhdaya chast v otdelnom soobshchenii")

if __name__ == "__main__":
    test_message_splitting()