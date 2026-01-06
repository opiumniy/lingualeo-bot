import requests
import httpx
import json
import os
import logging
from typing import Dict, List, Optional, Union
import aiofiles
import logging
from config import (
    API_URLS, DEFAULT_HEADERS, PAYLOAD_TEMPLATES,
    get_user_cookies_path, get_global_cookies_path, SAMPLE_COOKIES
)

USE_DATABASE = os.environ.get("DATABASE_URL") is not None

if USE_DATABASE:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lingualeo_pyth'))
    from db import save_user_cookies as db_save_cookies, get_user_cookies as db_get_cookies


class LingualeoAPIClient:
    """
    Универсальный клиент для взаимодействия с API Lingualeo.
    Поддерживает синхронные и асинхронные запросы, управление cookies.
    """

    def __init__(self, cookies: Optional[str] = None, user_id: Optional[int] = None):
        self.cookies = cookies or ""
        self.user_id = user_id
        self.headers = DEFAULT_HEADERS.copy()
        if self.cookies:
            self.headers['Cookie'] = self.cookies
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.async_client = None
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        self.async_client = httpx.AsyncClient(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_client:
            await self.async_client.aclose()

    def load_cookies(self, user_id: Optional[int] = None) -> bool:
        """
        Загружает cookies из файла пользователя.
        Для TG бота глобальный fallback отключен - каждый пользователь должен авторизоваться.
        """
        effective_user_id = user_id or self.user_id
        if effective_user_id:
            path = get_user_cookies_path(effective_user_id)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.cookies = f.read().strip()
                if self.cookies:
                    self.headers['Cookie'] = self.cookies
                    self.session.headers.update({'Cookie': self.cookies})
                    return True
        self.logger.warning(f"Cookies не найдены для user_id {effective_user_id}")
        return False

    async def load_user_cookies_async(self, user_id: int) -> bool:
        """
        Асинхронно загружает cookies пользователя.
        Приоритет: база данных -> файл пользователя -> глобальный файл
        """
        logger = logging.getLogger(__name__)

        # Сначала пробуем базу данных (если доступна)
        if USE_DATABASE:
            try:
                cookies_from_db = await db_get_cookies(user_id)
                if cookies_from_db:
                    self.cookies = cookies_from_db
                    self.headers['Cookie'] = self.cookies
                    logger.info(f"Cookies загружены из БД для user_id {user_id}")
                    return True
                else:
                    logger.debug(f"Cookies не найдены в БД для user_id {user_id}")
            except Exception as e:
                logger.error(f"Ошибка загрузки cookies из БД: {e}")

        # Fallback на пользовательский файл
        user_path = get_user_cookies_path(user_id)
        logger.debug(f"Проверяем пользовательский файл cookies: {user_path}")

        if os.path.exists(user_path):
            try:
                async with aiofiles.open(user_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.cookies = content.strip()

                if self.cookies:
                    self.headers['Cookie'] = self.cookies
                    logger.info(f"Пользовательские cookies загружены для user_id {user_id}")
                    return True
                else:
                    logger.warning(f"Пустой файл cookies: {user_path}")
            except Exception as e:
                logger.error(f"Ошибка чтения пользовательского файла cookies {user_path}: {e}")

        # НЕ используем глобальный файл для TG бота - каждый пользователь должен авторизоваться сам
        logger.info(f"Cookies не найдены для user_id {user_id} - требуется авторизация через /login")
        return False

    def login(self, email: str, password: str) -> Dict:
        """
        Синхронный логин и сохранение cookies.
        """
        url = API_URLS['auth']
        payload = PAYLOAD_TEMPLATES['login'].copy()
        payload['credentials']['email'] = email
        payload['credentials']['password'] = password
        self.logger.debug(f"Sending login request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"Login response: {response.text}")
        response.raise_for_status()
        # Сохраняем cookies
        cookies_str = '; '.join([f"{k}={v}" for k, v in response.cookies.items()])
        self.cookies = cookies_str
        self.headers['Cookie'] = cookies_str
        self.session.headers.update({'Cookie': cookies_str})
        # Сохраняем в файл
        if self.user_id:
            path = get_user_cookies_path(self.user_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(cookies_str)
        return response.json()

    async def login_async(self, email: str, password: str, user_id: int) -> Dict:
        """
        Асинхронный логин для TG бота.
        Сохраняет cookies в базу данных (если доступна) и в файл.
        """
        logger = logging.getLogger(__name__)
        url = API_URLS['auth']
        payload = PAYLOAD_TEMPLATES['login'].copy()
        payload['credentials']['email'] = email
        payload['credentials']['password'] = password
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        cookies_str = '; '.join([f"{k}={v}" for k, v in response.cookies.items()])
        self.cookies = cookies_str
        self.headers['Cookie'] = cookies_str
        
        # Сохраняем в базу данных (приоритет)
        if USE_DATABASE:
            try:
                await db_save_cookies(user_id, cookies_str)
                logger.info(f"Cookies сохранены в БД для user_id {user_id}")
            except Exception as e:
                logger.error(f"Ошибка сохранения cookies в БД: {e}")
        
        # Также сохраняем в файл (backup)
        path = get_user_cookies_path(user_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(cookies_str)
        
        return response.json()

    def add_word(self, word: str, translation: str) -> Dict:
        """
        Добавляет одно слово синхронно.
        """
        if not self.load_cookies(self.user_id):
            raise ValueError("Cookies not found. Login first.")
        url = API_URLS['set_words']
        payload = PAYLOAD_TEMPLATES['add_word'].copy()
        payload['data'][0]['valueList']['wordValue'] = word
        payload['data'][0]['valueList']['translation']['tr'] = translation
        self.logger.debug(f"Sending add_word request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"add_word response: {response.text}")
        response.raise_for_status()
        return response.json()

    def get_training_words_alternative(self) -> Dict:
        """
        Альтернативный метод получения слов для тренировки.
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_get_repetition",
            "data": {"wordSetId": 1, "limit": 10},
            "iDs": [{"y": ym_uid}]
        }

        self.logger.debug(f"Sending get_training_words_alternative request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"get_training_words_alternative response: {response.text}")
        response.raise_for_status()
        return response.json()

    def get_dictionary_words(self) -> Dict:
        """
        Получаем слова из словаря пользователя для тренировки.
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/GetWords'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "apiVersion": "1.0.1",
            "iDs": [{"y": ym_uid}],
            "data": {
                "includeUserTranslations": 1,
                "limit": 20,
                "offset": 0,
                "wordSetId": 1
            }
        }

        self.logger.debug(f"Sending get_dictionary_words request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"get_dictionary_words response: {response.text}")
        response.raise_for_status()
        return response.json()

    def process_training_answer_batch(self, training_results: dict) -> Dict:
        """
        Отправляет все результаты тренировки одним запросом (word_set_repetition).
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

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

        self.logger.debug(f"Sending process_training_answer_batch request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"process_training_answer_batch response: {response.text}")
        response.raise_for_status()
        return response.json()

    async def process_training_answer_async(self, user_id: int, word_id: int, translate_id: int, result: int) -> Dict:
        """
        Асинхронно отправляет ответ на вопрос тренировки (word_set_repetition).
        """
        if not await self.load_user_cookies_async(user_id):
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_set_repetition",
            "data": {
                "words": {str(word_id): translate_id},
                "wordSetId": 0
            },
            "iDs": [{"y": ym_uid}]
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def add_word_async(self, word: str, translation: str, user_id: int) -> str:
        """
        Асинхронно добавляет слово для TG бота.
        """
        if not await self.load_user_cookies_async(user_id):
            return "Пожалуйста, сначала войдите в систему!"
        url = API_URLS['set_words']
        payload = PAYLOAD_TEMPLATES['add_word'].copy()
        payload['data'][0]['valueList']['wordValue'] = word
        payload['data'][0]['valueList']['translation']['tr'] = translation
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(url, json=payload)
        if response.status_code == 200:
            return "Слово добавлено успешно!"
        else:
            return f"Ошибка добавления слова! Статус: {response.status_code}, Ответ: {response.text}"

    def add_words_bulk(self, csv_file: str) -> str:
        """
        Добавляет слова из CSV файла (для bulk add).
        CSV формат: word;translation
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Use global cookies.")
        url = API_URLS['set_words']
        words_list = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            for row in reader:
                if row and len(row) >= 2:
                    words_list.append({'word': row[0].strip(), 'translation': row[1].strip()})
        if not words_list:
            return "Нет слов для добавления."
        # Для bulk используем простой payload как в оригинальном bot.py
        payload = {
            "data": [{"word_value": w['word'], "translate_value": w['translation']} for w in words_list],
            "apiVersion": "1.0.1",
        }
        response = self.session.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return f"Добавлено {len(words_list)} слов успешно."
        else:
            return f"Ошибка bulk добавления: {response.status_code} - {response.text}"

    def export_all_words(self) -> List[Dict]:
        """
        Экспортирует все слова (для trainer).
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = API_URLS['load_words']
        # Извлекаем ID из cookies: предпочитаем _ym_uid, fallback на lingualeouid
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")
        payload = PAYLOAD_TEMPLATES['load_words'].copy()
        payload['iDs'] = [{'y': ym_uid}]
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])

    def get_training_words(self) -> Dict:
        """
        Получает слова для тренировки (word_get_repetition).
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_get_repetition",
            "data": {"wordSetId": 1},
            "iDs": [{"y": ym_uid}]
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def get_training_words_async(self, user_id: int) -> Dict:
        """
        Асинхронно получает слова для тренировки (word_get_repetition).
        """
        if not await self.load_user_cookies_async(user_id):
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_get_repetition",
            "data": {"wordSetId": 0},
            "iDs": [{"y": ym_uid}]
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def process_training_answer(self, word_id: int, translate_id: int, result: int) -> Dict:
        """
        Отправляет ответ на вопрос тренировки (word_set_repetition).
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/ProcessTraining'
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_set_repetition",
            "data": {
                "words": {str(word_id): translate_id},
                "wordSetId": 0
            },
            "iDs": [{"y": ym_uid}]
        }

        self.logger.debug(f"Sending process_training_answer request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload)
        self.logger.debug(f"process_training_answer response: {response.text}")
        response.raise_for_status()
        return response.json()

    def get_learning_main(self) -> Dict:
        """
        Получает основную информацию о тренировках через API getLearningMain.
        Возвращает данные с количеством слов для повторения.
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        url = 'https://api.lingualeo.com/getLearningMain'

        # Используем точные заголовки из curl примера
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "content-type": "application/json",
            "dnt": "1",
            "origin": "https://lingualeo.com",
            "priority": "u=1, i",
            "referer": "https://lingualeo.com/ru/training/words",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
        }

        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        payload = {
            "apiVersion": "1.0.0",
            "wordSetId": 1,
            "iDs": [{"y": ym_uid}]
        }

        self.logger.debug(f"Sending get_learning_main request to {url} with payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, headers=headers, json=payload)
        self.logger.debug(f"get_learning_main response: {response.text}")
        response.raise_for_status()
        return response.json()


def fix_process_training_answer_batch(client, training_results):
    """
    Исправленная версия process_training_answer_batch для применения к
    существующему экземпляру LingualeoAPIClient.
    
    Решает проблему с неправильной маркировкой слов как "ошибленных"
    после успешного прохождения тренировки.
    
    Args:
        client (LingualeoAPIClient): экземпляр API-клиента
        training_results (dict): результаты тренировки с ID слов и переводов
    
    Returns:
        dict: ответ от сервера
    """
    if not client.load_cookies():
        raise ValueError("Cookies not found. Login first.")
    
    url = 'https://api.lingualeo.com/ProcessTraining'
    
    # Извлекаем ID из cookies
    cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip()
                  for c in client.cookies.split(';') if '=' in c}
    ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
    if not ym_uid:
        raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

    # ИСПРАВЛЕНИЕ: нормализуем типы данных
    # Ключи должны быть строками, значения - числами (int)
    normalized_results = {}
    for word_id, translate_id in training_results.items():
        try:
            # Преобразуем word_id в строку, translate_id в число
            normalized_results[str(word_id)] = int(translate_id)
        except (ValueError, TypeError) as e:
            logging.warning(f"Ошибка преобразования типов данных: word_id={word_id}, translate_id={translate_id}: {e}")
            # В случае ошибки преобразования используем значения как есть,
            # но с приведенным типом ключа к строке
            normalized_results[str(word_id)] = translate_id
    
    payload = {
        "api_call": "process_training",
        "apiVersion": "1.0.1",
        "trainingName": "word_set_repetition",
        "data": {
            "words": normalized_results,
            "wordSetId": 0
        },
        "iDs": [{"y": ym_uid}]
    }

    response = client.session.post(url, json=payload)
    response.raise_for_status()
    return response.json()