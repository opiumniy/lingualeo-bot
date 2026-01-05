import requests
import httpx
import json
import os
import logging
from typing import Dict, List, Optional, Union
import aiofiles
from config import (
    API_URLS, DEFAULT_HEADERS, PAYLOAD_TEMPLATES,
    get_user_cookies_path, get_global_cookies_path, SAMPLE_COOKIES
)


class LingualeoAPIClient:
    """
    Универсальный клиент для взаимодействия с API Lingualeo.
    Поддерживает синхронные и асинхронные запросы, управление cookies.
    """

    def __init__(self, cookies: Optional[str] = None, user_id: Optional[int] = None):
        self.cookies = cookies or SAMPLE_COOKIES
        self.user_id = user_id
        self.headers = DEFAULT_HEADERS.copy()
        self.headers['Cookie'] = self.cookies
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.async_client = None

    async def __aenter__(self):
        self.async_client = httpx.AsyncClient(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_client:
            await self.async_client.aclose()

    def load_cookies(self, user_id: Optional[int] = None) -> bool:
        """
        Загружает cookies из файла пользователя или глобального.
        """
        if user_id:
            path = get_user_cookies_path(user_id)
        else:
            path = get_global_cookies_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.cookies = f.read().strip()
            self.headers['Cookie'] = self.cookies
            self.session.headers.update({'Cookie': self.cookies})
            return True
        return False

    async def load_user_cookies_async(self, user_id: int) -> bool:
        """
        Асинхронно загружает cookies пользователя с fallback на глобальный файл.
        """
        logger = logging.getLogger(__name__)

        # Сначала пробуем пользовательский файл
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

        # Если пользовательский файл не найден или пустой, пробуем глобальный файл
        global_path = get_global_cookies_path()
        logger.debug(f"Проверяем глобальный файл cookies: {global_path}")

        if os.path.exists(global_path):
            try:
                async with aiofiles.open(global_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.cookies = content.strip()

                if self.cookies:
                    self.headers['Cookie'] = self.cookies
                    logger.info(f"Глобальные cookies загружены для user_id {user_id}")
                    return True
                else:
                    logger.warning(f"Пустой глобальный файл cookies: {global_path}")
            except Exception as e:
                logger.error(f"Ошибка чтения глобального файла cookies {global_path}: {e}")

        logger.error(f"Не удалось загрузить cookies для user_id {user_id}")
        return False

    def login(self, email: str, password: str) -> Dict:
        """
        Синхронный логин и сохранение cookies.
        """
        url = API_URLS['auth']
        payload = PAYLOAD_TEMPLATES['login'].copy()
        payload['credentials']['email'] = email
        payload['credentials']['password'] = password
        response = self.session.post(url, json=payload)
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
        """
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
        # Сохраняем асинхронно
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
        response = self.session.post(url, json=payload)
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

        response = self.session.post(url, json=payload)
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

        response = self.session.post(url, json=payload)
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

        response = self.session.post(url, json=payload)
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

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()