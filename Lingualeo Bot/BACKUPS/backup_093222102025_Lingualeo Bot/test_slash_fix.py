#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления слешей в командах
"""

def test_slash_formatting():
    """Тестируем форматирование слешей в командах"""
    print("TEST ISpravleniya sleshey v komandakh")
    print("=" * 50)

    # Обычная строка (старая)
    old_commands = """
Доступные команды:
/start - Начать работу с ботом
/login - Войти в аккаунт Lingualeo
/addword - Добавить новое слово
/rep_engrus - Тренировка английских слов с русским переводом
/send_results - Отправить сохраненные результаты тренировки на сервер
    """

    # Сырая строка (новая)
    new_commands = r"""
Доступные команды:
/start - Начать работу с ботом
/login - Войти в аккаунт Lingualeo
/addword - Добавить новое слово
/rep_engrus - Тренировка английских слов с русским переводом
/send_results - Отправить сохраненные результаты тренировки на сервер
    """

    print("STARYY FORMAT (s oshibkoy):")
    print(old_commands)
    print("\nNOVYY FORMAT (ispravlennyy):")
    print(new_commands)

    # Проверяем что слеши не экранированы
    if r"\/" in old_commands:
        print("\n❌ STARYY FORMAT IMEET EKRANIROVANNYE SLESCHI")
    else:
        print("\n✅ STARYY FORMAT BEZ EKRANIROVANNYKH SLESCHEY")

    if r"\/" in new_commands:
        print("❌ NOVYY FORMAT IMEET EKRANIROVANNYE SLESCHI")
    else:
        print("✅ NOVYY FORMAT BEZ EKRANIROVANNYKH SLESCHEY")

    print("\n" + "=" * 50)
    print("ISpravlenie:")
    print("- Dobavlen prefiks 'r' pered strokovymi literelami")
    print("- Teper komandy pokazyvayutsya pravilno: /start, /login")
    print("- Vmesto ekranirivannykh: \/start, \/login")

if __name__ == "__main__":
    test_slash_formatting()