import logging
import json
from api_client import LingualeoAPIClient

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_repeat_count(client):
    """Получает текущее количество слов для повторения"""
    try:
        response = client.get_learning_main()
        logger.debug(f"Raw repeat count response: {json.dumps(response, indent=2)}")
        
        if response.get('status') == 'ok':
            data = response.get('data', [])
            for section in data:
                if 'word' in section:
                    word_trainings = section['word']
                    for training in word_trainings:
                        if training.get('tag') == 'repetition':
                            counter = training.get('counter', {})
                            words_count = counter.get('words', 0)
                            logger.info(f"Найдено {words_count} слов для повторения")
                            return words_count
            
            logger.warning("Тренировка повторения не найдена в ответе")
            return 0
        else:
            logger.error(f"Ошибка API: {response.get('status')}")
            return 0
    except Exception as e:
        logger.error(f"Ошибка при получении repeat count: {str(e)}")
        return 0

def simulate_training():
    """Симулирует полный цикл тренировки"""
    try:
        # Инициализация клиента с глобальными cookies
        client = LingualeoAPIClient()
        if not client.load_cookies():
            logger.error("Не удалось загрузить cookies")
            return
        
        logger.info("=== Начало симуляции тренировки ===")
        
        # Шаг 1: Получить начальное количество повторений
        initial_count = get_repeat_count(client)
        
        # Шаг 2: Получить слова для тренировки
        words_response = client.get_training_words()
        logger.debug(f"Полученные слова: {json.dumps(words_response, indent=2)}")
        
        words = words_response.get('game', {}).get('user_words', [])
        if not words:
            logger.error("Не получены слова для тренировки")
            return
        
        logger.info(f"Получено {len(words)} слов для тренировки")
        
        # Шаг 3: Симулировать успешные ответы (все слова правильные)
        training_results = {}
        for word in words:
            word_id = word.get('word_id')
            translate_id = word.get('translate_id')
            
            if word_id and translate_id:
                training_results[str(word_id)] = translate_id
                logger.debug(f"Симулирован правильный ответ: word_id={word_id}, translate_id={translate_id}")
        
        # Шаг 4: Отправить результаты
        result_response = client.process_training_answer_batch(training_results)
        logger.debug(f"Ответ на отправку результатов: {json.dumps(result_response, indent=2)}")
        
        # Шаг 5: Получить финальное количество повторений
        final_count = get_repeat_count(client)
        
        logger.info("=== Результаты симуляции ===")
        logger.info(f"Начальное количество: {initial_count}")
        logger.info(f"Финальное количество: {final_count}")
        logger.info(f"Разница: {final_count - initial_count}")
        
        if final_count == initial_count:
            logger.info("Успех: Количество повторений не изменилось")
        else:
            logger.warning(f"Проблема: Изменение в {final_count - initial_count} словах")
    
    except Exception as e:
        logger.error(f"Ошибка в симуляции: {str(e)}", exc_info=True)

if __name__ == "__main__":
    simulate_training()
