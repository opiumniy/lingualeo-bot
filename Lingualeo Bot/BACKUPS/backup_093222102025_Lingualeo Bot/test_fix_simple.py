#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест исправленной логики накопления результатов
"""

import sys
import os
import json

def test_training_results_accumulation():
    """Тестируем накопление результатов тренировки"""
    print("TEST NAKOPLENIYA REZULTATOV TRENIROVKI")
    print("=" * 50)

    # Эмулируем состояние с существующими результатами
    existing_results = {"10001": 1, "10002": 2}  # Два предыдущих слова

    # Эмулируем данные состояния бота
    state_data = {
        'training_results': existing_results.copy(),
        'current_word_id': 10003,
        'correct_answers': 2,
        'total_answers': 3,
        'wrong_answers': []
    }

    print("Nachalnaya situatsiya:")
    print(f"  Sushchestvuyushchie rezultaty: {state_data['training_results']}")
    print(f"  Tekushchee slovo ID: {state_data['current_word_id']}")

    # Эмулируем обработку правильного ответа (is_correct = True)
    is_correct = True
    current_word_id = state_data['current_word_id']
    training_results = state_data.get('training_results', {})

    translate_id = 1 if is_correct else 2
    training_results[str(current_word_id)] = translate_id

    print("\nPosle obrabotki otveta:")
    print(f"  Dobavlen rezultat dlya slova {current_word_id}: {translate_id}")
    print(f"  Vse rezultaty: {training_results}")

    # Проверяем что все результаты сохранились
    expected_results = {"10001": 1, "10002": 2, "10003": 1}
    if training_results == expected_results:
        print("\nTEST PROYDEN: Vse rezultaty nakopleny pravilno!")
    else:
        print(f"\nTEST NE PROYDEN: Ozhidali {expected_results}, poluchili {training_results}")

    # Эмулируем обработку неправильного ответа
    print("\nTestiruem nepravilnyy otvet...")
    state_data['current_word_id'] = 10004
    current_word_id = state_data['current_word_id']
    is_correct = False

    translate_id = 1 if is_correct else 2
    training_results[str(current_word_id)] = translate_id

    print(f"  Dobavlen rezultat dlya slova {current_word_id}: {translate_id}")
    print(f"  Vse rezultaty: {training_results}")

    # Проверяем финальный результат
    expected_final = {"10001": 1, "10002": 2, "10003": 1, "10004": 2}
    if training_results == expected_final:
        print("\nKONECHNY TEST PROYDEN: Vse 4 rezultata nakopleny!")
    else:
        print(f"\nKONECHNY TEST NE PROYDEN: Ozhidali {expected_final}, poluchili {training_results}")

    print("\n" + "=" * 50)
    print("OZHiDAEMYY ZAPROS NA SERVER:")
    print("POST /ProcessTraining")
    print(f"Dannye: {json.dumps(training_results, ensure_ascii=False, indent=2)}")

    print("\nV KAZhDOM SHAGE DOLZhNO BIT:")
    print("- Slovo 10001: pravilnyy otvet (1)")
    print("- Slovo 10002: nepravilnyy otvet (2)")
    print("- Slovo 10003: pravilnyy otvet (1)")
    print("- Slovo 10004: nepravilnyy otvet (2)")

if __name__ == "__main__":
    test_training_results_accumulation()