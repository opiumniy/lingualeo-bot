#!/usr/bin/env python3
"""
Тест интервалов повторения - проверяем правильность расчета интервалов
"""

def format_repeat_interval_test(minutes: int) -> str:
    """
    Testovaya funkciya dlya pravil'nogo formatirovaniya intervalov povtoreniya
    """
    if minutes >= 525600:  # 365 dney * 24 chasa * 60 minut
        years = minutes // 525600
        return f"+ {years} g."
    elif minutes >= 43200:  # 30 dney * 24 chasa * 60 minut
        months = minutes // 43200
        return f"+ {months} mes."
    elif minutes >= 10080:  # 7 dney * 24 chasa * 60 minut
        weeks = minutes // 10080
        return f"+ {weeks} ned."
    elif minutes >= 1440:  # 24 chasa * 60 minut
        days = minutes // 1440
        return f"+ {days} d."
    elif minutes >= 480:  # 8 chasov
        hours = minutes // 60
        return f"- {hours} ch."
    else:
        return "- 6 ch."

# Testovye dannye iz real'nogo otveta servera
test_cases = [
    (480, "- 8 ch."),    # 480 minut = 8 chasov
    (5280, "+ 3 d."),   # 5280 minut = 88 chasov = 3.67 dney
    (4800, "+ 3 d."),   # 4800 minut = 80 chasov = 3.33 dney
    (10080, "+ 1 ned."), # 10080 minut = 7 dney
    (43200, "+ 1 mes."), # 43200 minut = 30 dney
    (525600, "+ 1 g."),  # 525600 minut = 365 dney
]

print("TESTIROVANIE INTERVALOV POVTORENIYA")
print("=" * 50)

for minutes, expected in test_cases:
    result = format_repeat_interval_test(minutes)
    status = "OK" if result == expected else "ERROR"
    print(f"{status} {minutes} min -> {result} (ozhidali: {expected})")

print("\nREALNYE DANNYE IZ OTVETA SERVERA:")
print("-" * 50)

# Realnye dannye iz curl otveta
real_data = [
    {"word": "bespoke", "repeat_interval": 5280, "repeat_at": "2026-09-26 20:00:00+00"},
    {"word": "breeze", "repeat_interval": 480, "repeat_at": "2025-10-20 20:00:00+00"},
    {"word": "cattle", "repeat_interval": 5280, "repeat_at": "2026-09-26 20:00:00+00"},
    {"word": "chant", "repeat_interval": 5280, "repeat_at": "2026-09-26 20:00:00+00"},
    {"word": "go on", "repeat_interval": 4800, "repeat_at": "2026-04-09 04:00:00+00"},
]

for item in real_data:
    word = item["word"]
    minutes = item["repeat_interval"]
    formatted = format_repeat_interval_test(minutes)
    print(f"WORD {word}: {minutes} min -> {formatted}")

print("\nTEST ZAVERSHEN")

print("\n" + "="*50)
print("SOVETY PO ISPOL'ZOVANIYU:")
print("="*50)
print("1. Zapustite trenirovku: /rep_engrus")
print("2. Projdyte neskol'ko slov")
print("3. V konce dolzhny uvidet' pravil'nye intervaly:")
print("   - 480 min -> - 8 ch. (8 chasov)")
print("   - 5280 min -> + 3 d. (3 dnya)")
print("   - 10080 min -> + 1 ned. (1 nedelya)")
print("4. Esli vse slova pokazyvayut '- 8 ch.' - est' problema")
print("5. Esli vidite '+ 3 d.', '+ 1 ned.' - vse rabotaet pravil'no")