import logging
import json
import time
from api_client import LingualeoAPIClient, fix_process_training_answer_batch

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
    handlers=[
        logging.FileHandler('test_real_translates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_repeat_count(client):
    try:
        response = client.get_learning_main()
        if response.get('status') == 'ok':
            data = response.get('data', [])
            for section in data:
                if 'word' in section:
                    word_trainings = section['word']
                    for training in word_trainings:
                        if training.get('tag') == 'repetition':
                            counter = training.get('counter', {})
                            return counter.get('words', 0)
        return 0
    except Exception as e:
        logger.error(f"Error getting repeat count: {e}")
        return 0

def create_translates_for_word(word, all_words):
    word_id = word.get('word_id', 0)
    word_value = word.get('word_value', '')
    correct_translate_value = word.get('correct_translate_value', '')
    translate_id = word.get('translate_id', 1)
    
    translates = [{'id': translate_id, 'value': correct_translate_value}]
    
    if 'translates' in word and isinstance(word['translates'], list):
        for tr in word['translates']:
            if isinstance(tr, dict) and tr.get('id') != translate_id:
                translates.append({'id': tr.get('id', 0), 'value': tr.get('value', '')})
    
    if len(translates) < 4:
        import random
        other_words = [w for w in all_words if w.get('word_id') != word_id]
        random.shuffle(other_words)
        
        for other_word in other_words:
            if len(translates) >= 4:
                break
            other_id = other_word.get('translate_id', 0)
            existing_ids = [t['id'] for t in translates]
            if other_id not in existing_ids:
                translates.append({
                    'id': other_id,
                    'value': other_word.get('correct_translate_value', '')
                })
    
    logger.debug(f"Word '{word_value}' translates: {translates}")
    return translates

def test_translates_parsing():
    logger.info("=== TEST: Translates Parsing ===")
    
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Failed to load cookies")
        return False
    
    words_response = client.get_training_words()
    words = words_response.get('game', {}).get('user_words', [])
    
    if not words:
        logger.error("No words returned from API")
        return False
    
    logger.info(f"Got {len(words)} words from API")
    
    for i, word in enumerate(words[:5]):
        word_id = word.get('word_id')
        word_value = word.get('word_value')
        translate_id = word.get('translate_id')
        correct_translate = word.get('correct_translate_value')
        
        translates = create_translates_for_word(word, words)
        
        logger.info(f"Word {i+1}: '{word_value}' (id={word_id})")
        logger.info(f"  correct_translate_id: {translate_id}")
        logger.info(f"  translates count: {len(translates)}")
        for j, t in enumerate(translates):
            is_correct = "✓ CORRECT" if t['id'] == translate_id else ""
            logger.info(f"    [{j}] id={t['id']}, value='{t['value']}' {is_correct}")
        
        if len(translates) < 4:
            logger.warning(f"  WARNING: Less than 4 translates!")
    
    return True

def test_wrong_answer_with_different_ids():
    logger.info("=== TEST: Wrong Answers with Different IDs ===")
    
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Failed to load cookies")
        return False
    
    initial_count = get_repeat_count(client)
    logger.info(f"Initial repeat count: {initial_count}")
    
    words_response = client.get_training_words()
    words = words_response.get('game', {}).get('user_words', [])
    
    if len(words) < 2:
        logger.error("Need at least 2 words for this test")
        return False
    
    test_results = {}
    
    for i, word in enumerate(words[:5]):
        word_id = word.get('word_id')
        correct_translate_id = word.get('translate_id', 1)
        word_value = word.get('word_value')
        
        translates = create_translates_for_word(word, words)
        
        wrong_translates = [t for t in translates if t['id'] != correct_translate_id]
        
        if wrong_translates:
            wrong_id = wrong_translates[0]['id']
            test_results[str(word_id)] = wrong_id
            
            logger.info(f"Word '{word_value}' (id={word_id}): "
                       f"correct_id={correct_translate_id}, "
                       f"sending WRONG id={wrong_id}")
        else:
            test_results[str(word_id)] = correct_translate_id
            logger.info(f"Word '{word_value}' (id={word_id}): "
                       f"no wrong translates, sending correct_id={correct_translate_id}")
    
    logger.info(f"Sending batch results: {test_results}")
    
    try:
        response = fix_process_training_answer_batch(client, test_results)
        logger.info(f"Server response status: {response.get('status')}")
        
        if 'game' in response:
            game_data = response.get('game', {})
            logger.info(f"Game data keys: {list(game_data.keys())}")
            
            user_words = game_data.get('user_words', [])
            for w in user_words[:5]:
                logger.info(f"  word_id={w.get('word_id')}, "
                           f"repeat_at={w.get('repeat_at')}, "
                           f"training_state={w.get('training_state')}, "
                           f"training_result={w.get('training_result')}")
    except Exception as e:
        logger.error(f"Error sending batch: {e}")
        return False
    
    time.sleep(2)
    final_count = get_repeat_count(client)
    logger.info(f"Final repeat count: {final_count}")
    logger.info(f"Difference: {final_count - initial_count}")
    
    if final_count >= initial_count:
        logger.info("SUCCESS: Wrong answers should keep/increase repeat count (LEARNING state)")
        return True
    else:
        logger.warning("UNEXPECTED: Repeat count decreased after wrong answers")
        return False

def test_correct_vs_wrong_comparison():
    logger.info("=== TEST: Correct vs Wrong Answer Comparison ===")
    
    client = LingualeoAPIClient()
    if not client.load_cookies():
        logger.error("Failed to load cookies")
        return False
    
    words_response = client.get_training_words()
    words = words_response.get('game', {}).get('user_words', [])
    
    if len(words) < 4:
        logger.error("Need at least 4 words for this test")
        return False
    
    initial_count = get_repeat_count(client)
    logger.info(f"Initial repeat count: {initial_count}")
    
    test_results = {}
    
    for i, word in enumerate(words[:2]):
        word_id = word.get('word_id')
        correct_translate_id = word.get('translate_id', 1)
        test_results[str(word_id)] = correct_translate_id
        logger.info(f"Word {i+1} CORRECT: word_id={word_id}, translate_id={correct_translate_id}")
    
    for i, word in enumerate(words[2:4]):
        word_id = word.get('word_id')
        correct_translate_id = word.get('translate_id', 1)
        
        translates = create_translates_for_word(word, words)
        wrong_translates = [t for t in translates if t['id'] != correct_translate_id]
        
        if wrong_translates:
            wrong_id = wrong_translates[0]['id']
            test_results[str(word_id)] = wrong_id
            logger.info(f"Word {i+3} WRONG: word_id={word_id}, "
                       f"correct={correct_translate_id}, sending={wrong_id}")
        else:
            test_results[str(word_id)] = correct_translate_id
            logger.warning(f"Word {i+3} (no wrong available): word_id={word_id}")
    
    logger.info(f"Mixed batch: {test_results}")
    
    try:
        response = fix_process_training_answer_batch(client, test_results)
        logger.info(f"Response status: {response.get('status')}")
        
        if 'game' in response:
            user_words = response.get('game', {}).get('user_words', [])
            for w in user_words:
                word_id = w.get('word_id')
                if str(word_id) in test_results:
                    was_correct = test_results[str(word_id)] == words_response.get('game', {}).get('user_words', [])
                    logger.info(f"  Result for word_id={word_id}: "
                               f"repeat_at={w.get('repeat_at')}, "
                               f"training_result={w.get('training_result')}, "
                               f"training_state={w.get('training_state')}")
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    
    time.sleep(2)
    final_count = get_repeat_count(client)
    logger.info(f"Final repeat count: {final_count}")
    
    return True

def test_shuffle_logging():
    logger.info("=== TEST: Shuffle and Logging ===")
    
    import random
    
    sample_words = [
        {
            'word_id': 12345,
            'word_value': 'test_word_1',
            'correct_translate_value': 'тестовое слово 1',
            'translate_id': 100
        },
        {
            'word_id': 12346,
            'word_value': 'test_word_2',
            'correct_translate_value': 'тестовое слово 2',
            'translate_id': 101
        },
        {
            'word_id': 12347,
            'word_value': 'test_word_3',
            'correct_translate_value': 'тестовое слово 3',
            'translate_id': 102
        },
        {
            'word_id': 12348,
            'word_value': 'test_word_4',
            'correct_translate_value': 'тестовое слово 4',
            'translate_id': 103
        }
    ]
    
    for word in sample_words:
        translates = create_translates_for_word(word, sample_words)
        
        shuffled = translates.copy()
        random.shuffle(shuffled)
        
        correct_id = word['translate_id']
        shuffled_ids = [t['id'] for t in shuffled]
        correct_index = next(
            (i for i, t in enumerate(shuffled) if t['id'] == correct_id),
            0
        )
        
        logger.info(f"Word '{word['word_value']}' (word_id={word['word_id']}): "
                   f"correct_id={correct_id}, "
                   f"shuffled_translate_ids={shuffled_ids}, "
                   f"correct_option_index={correct_index}")
    
    return True

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Real Translates Tests")
    logger.info("=" * 60)
    
    test_shuffle_logging()
    
    try:
        test_translates_parsing()
    except Exception as e:
        logger.error(f"test_translates_parsing failed: {e}")
    
    try:
        test_wrong_answer_with_different_ids()
    except Exception as e:
        logger.error(f"test_wrong_answer_with_different_ids failed: {e}")
    
    try:
        test_correct_vs_wrong_comparison()
    except Exception as e:
        logger.error(f"test_correct_vs_wrong_comparison failed: {e}")
    
    logger.info("=" * 60)
    logger.info("All tests completed")
    logger.info("=" * 60)
