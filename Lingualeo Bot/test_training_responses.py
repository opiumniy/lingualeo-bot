#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для анализа проблемы с маркировкой слов как "ошибленных"
даже при условии успешного повторения.
"""

import os
import json
import logging
from api_client import LingualeoAPIClient
from config import get_global_cookies_path, get_user_cookies_path

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('test_training_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_training')

def load_example_training_results():
    """
    Загружает пример результатов тренировки для тестирования.
    В реальном приложении эти данные заполняются на основе ответов пользователя.
    """
    try:
        # Пробуем загрузить из существующего файла
        if os.path.exists('training_results_example.json'):
            with open('training_results_example.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    # Или создаем тестовые данные
    return {
        "12345": 1,  # ID слова: ID перевода (1 = правильный перевод)
        "67890": 2,  
        "54321": 3
    }

def analyze_response_data(response_data):
    """
    Анализирует данные ответа от сервера Lingualeo.
    Проверяет, правильно ли отмечены слова как повторенные.
    """
    logger.info("Анализ данных ответа от сервера")
    
    if not response_data or 'status' not in response_data:
        logger.error("Неверный формат ответа: нет статуса")
        return False
    
    if response_data['status'] != 'ok':
        logger.error(f"Статус ответа не OK: {response_data['status']}")
        return False
    
    # Проверяем данные о словах
    if 'words' not in response_data or not response_data['words']:
        logger.error("В ответе нет данных о словах")
        return False
    
    logger.info(f"Количество слов в ответе: {len(response_data['words'])}")
    
    # Анализируем каждое слово
    words_with_error = []
    for word_data in response_data['words']:
        word_id = word_data.get('word_id')
        is_error = word_data.get('is_error', 0)
        
        logger.debug(f"Слово ID {word_id}: is_error={is_error}, repeat_interval={word_data.get('repeat_interval')}")
        
        if is_error:
            words_with_error.append(word_id)
    
    if words_with_error:
        logger.warning(f"Найдены слова с ошибкой: {words_with_error}")
    else:
        logger.info("Все слова отмечены без ошибок")
    
    return {
        'total_words': len(response_data['words']),
        'error_words': words_with_error,
        'response': response_data
    }

def test_send_with_different_formats():
    """
    Тестирование отправки результатов в разных форматах для выявления проблемы
    """
    logger.info("Начало теста отправки результатов в разных форматах")
    
    # Создаем клиент API
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Ошибка загрузки cookies")
        return False
    
    # Загружаем тестовые результаты
    results = load_example_training_results()
    logger.info(f"Загружены тестовые результаты: {results}")
    
    # ТЕСТ 1: Отправка оригинального формата
    logger.info("ТЕСТ 1: Отправка оригинального формата")
    response1 = client.process_training_answer_batch(results)
    analysis1 = analyze_response_data(response1)
    
    # ТЕСТ 2: Форматирование значений как числа
    logger.info("ТЕСТ 2: Форматирование значений как числа")
    numeric_results = {k: int(v) for k, v in results.items()}
    response2 = client.process_training_answer_batch(numeric_results)
    analysis2 = analyze_response_data(response2)
    
    # ТЕСТ 3: Форматирование всех ключей и значений как строки
    logger.info("ТЕСТ 3: Форматирование всех как строки")
    string_results = {str(k): str(v) for k, v in results.items()}
    response3 = client.process_training_answer_batch(string_results)
    analysis3 = analyze_response_data(response3)
    
    # Определение проблемы с типом данных
    logger.info("Сравнение результатов разных форматов:")
    logger.info(f"Тест 1 (оригинал): {len(analysis1['error_words']) if isinstance(analysis1, dict) else 'ОШИБКА'} слов с ошибками")
    logger.info(f"Тест 2 (числа): {len(analysis2['error_words']) if isinstance(analysis2, dict) else 'ОШИБКА'} слов с ошибками")
    logger.info(f"Тест 3 (строки): {len(analysis3['error_words']) if isinstance(analysis3, dict) else 'ОШИБКА'} слов с ошибками")
    
    # Сохраняем ответы для дальнейшего анализа
    with open('test_responses.json', 'w', encoding='utf-8') as f:
        json.dump({
            'test1': response1,
            'test2': response2,
            'test3': response3
        }, f, ensure_ascii=False, indent=2)
    
    logger.info("Ответы сохранены в test_responses.json")
    
    # ТЕСТ 4: Проверяем формат данных внутри API-клиента
    logger.info("ТЕСТ 4: Анализ процесса подготовки данных для запроса")
    original_process_training = client.process_training_answer_batch
    
    def patched_process_training(training_results):
        """Патч для перехвата и анализа данных перед отправкой"""
        logger.info("Перехват process_training_answer_batch")
        logger.info(f"Тип training_results: {type(training_results)}")
        
        # Получаем данные из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() 
                       for c in client.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        
        # Воссоздаем payload как в оригинальном методе
        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_set_repetition",
            "data": {
                "words": training_results,
                "wordSetId": 0
            },
            "iDs": [{"y": ym_uid}]
        }
        
        # Сохраняем конечный payload для анализа
        with open('debug_payload.json', 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Подготовленный payload: {json.dumps(payload, ensure_ascii=False)}")
        logger.info(f"words в payload: {training_results}")
        
        for word_id, translate_id in training_results.items():
            logger.debug(f"Анализ word_id={word_id} ({type(word_id)}), translate_id={translate_id} ({type(translate_id)})")
        
        # Вызываем оригинальный метод
        result = original_process_training(training_results)
        
        # Теперь посмотрим результат
        logger.info(f"Анализ результата с формами данных")
        for word in result.get('words', []):
            word_id = word.get('word_id')
            original_id = str(word_id) if isinstance(word_id, int) else word_id
            is_error = word.get('is_error', 0)
            translate_id = training_results.get(word_id) or training_results.get(str(word_id))
            
            logger.info(f"word_id: {word_id} ({type(word_id)}), translate_id: {translate_id}, is_error: {is_error}")
        
        return result
    
    # Заменяем метод на наш патч
    client.process_training_answer_batch = patched_process_training
    
    # Тестируем с патчем
    logger.info("Запуск теста с патчем для детального анализа")
    test_results = {
        "123": 1,
        "456": 2, 
        789: 3  # Специально одно значение как число
    }
    response4 = client.process_training_answer_batch(test_results)
    analyze_response_data(response4)
    
    logger.info("Тест завершен")
    
    return {
        'test1': analysis1,
        'test2': analysis2,
        'test3': analysis3
    }

def check_actual_server_response_format():
    """
    Проверка реального формата ответа сервера и формата запроса
    """
    logger.info("Проверка реального формата ответа сервера")
    
    # Берем единственное слово для тестирования
    test_results = {"123456": 1}
    
    # Создаем клиент API
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Ошибка загрузки cookies")
        return False
    
    response = client.process_training_answer_batch(test_results)
    
    # Анализируем полный ответ
    logger.info("Анализ полного ответа сервера:")
    for key, value in response.items():
        logger.info(f"Ключ: {key}, Тип: {type(value)}")
        
        if key == 'words' and isinstance(value, list) and value:
            logger.info("Детальный анализ слов:")
            for i, word in enumerate(value):
                logger.info(f"  Слово {i+1}:")
                for w_key, w_val in word.items():
                    logger.info(f"    {w_key}: {w_val} ({type(w_val)})")
    
    return response
    
def fix_training_results_structure():
    """
    Функция для создания фикса проблемы маркировки слов
    """
    logger.info("Создание исправления для проблемы маркировки слов")
    
    # Пример кода для фикса (на основе результатов анализа)
    fix_code = """
    def fixed_process_training_answer(client, training_results):
        \"\"\"
        Исправленная версия process_training_answer_batch
        \"\"\"
        # 1. Все ключи (word_id) должны быть строками
        # 2. Все значения (translate_id) должны быть целыми числами
        fixed_results = {}
        for word_id, translate_id in training_results.items():
            fixed_results[str(word_id)] = int(translate_id)
            
        # Используем исправленные данные
        return client.process_training_answer_batch(fixed_results)
    """
    
    # Создаем реальный исправленный метод
    def fixed_process_training_answer_batch(client, training_results):
        """Исправленная версия process_training_answer_batch"""
        # Исправляем типы данных перед отправкой
        fixed_results = {}
        for word_id, translate_id in training_results.items():
            fixed_results[str(word_id)] = int(translate_id)
            
        # Используем исправленные данные
        return client.process_training_answer_batch(fixed_results)
    
    # Тестируем исправленный метод
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Ошибка загрузки cookies")
        return False
    
    # Создаем смешанный набор данных для теста
    mixed_results = {
        "123": 1,  # строка -> число
        456: "2",  # число -> строка
        "789": "3",  # строка -> строка
        1010: 4  # число -> число
    }
    
    original_response = client.process_training_answer_batch(mixed_results)
    fixed_response = fixed_process_training_answer_batch(client, mixed_results)
    
    # Анализируем и сравниваем результаты
    logger.info("=== СРАВНЕНИЕ РЕЗУЛЬТАТОВ ===")
    
    original_analysis = analyze_response_data(original_response)
    fixed_analysis = analyze_response_data(fixed_response)
    
    if isinstance(original_analysis, dict) and isinstance(fixed_analysis, dict):
        logger.info(f"Оригинальный метод: {len(original_analysis['error_words'])} слов с ошибками")
        logger.info(f"Исправленный метод: {len(fixed_analysis['error_words'])} слов с ошибками")
        
        if len(original_analysis['error_words']) > len(fixed_analysis['error_words']):
            logger.info("✅ ИСПРАВЛЕНИЕ РАБОТАЕТ! Количество ошибок уменьшилось.")
        elif len(original_analysis['error_words']) == len(fixed_analysis['error_words']):
            logger.info("⚠️ Количество ошибок не изменилось.")
        else:
            logger.info("❌ Странно, количество ошибок увеличилось.")
    
    # Сохраняем результаты в файл для дальнейшего анализа
    with open('fixed_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'original': original_response,
            'fixed': fixed_response
        }, f, ensure_ascii=False, indent=2)
    
    return {
        'original': original_analysis,
        'fixed': fixed_analysis,
        'fix_code': fix_code
    }

def main():
    """Основная функция для запуска тестов"""
    logger.info("=== Запуск анализа проблемы с маркировкой тренировки ===")
    
    # Анализируем формат запроса и ответа
    logger.info("1. Проверка формата ответа сервера")
    server_response = check_actual_server_response_format()
    
    logger.info("\n2. Тестирование разных форматов")
    test_results = test_send_with_different_formats()
    
    logger.info("\n3. Создание и тестирование исправления")
    fix_results = fix_training_results_structure()
    
    logger.info("\n=== Итоги анализа ===")
    if isinstance(fix_results, dict) and 'original' in fix_results and 'fixed' in fix_results:
        original = fix_results['original']
        fixed = fix_results['fixed']
        
        if isinstance(original, dict) and isinstance(fixed, dict):
            logger.info(f"Исходный метод: {len(original['error_words'])} проблемных слов из {original['total_words']}")
            logger.info(f"Исправленный: {len(fixed['error_words'])} проблемных слов из {fixed['total_words']}")
            
            reduction = len(original['error_words']) - len(fixed['error_words'])
            if reduction > 0:
                logger.info(f"✅ Исправление успешно убрало {reduction} ошибок!")
                logger.info("Рекомендуется внести исправление в код приложения.")
            else:
                logger.info("⚠️ Исправление не улучшило результат. Требуется дополнительный анализ.")
    
    logger.info("=== Анализ завершен ===")

if __name__ == "__main__":
    main()