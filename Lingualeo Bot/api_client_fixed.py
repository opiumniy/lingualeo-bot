#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленная версия API-клиента Lingualeo с фиксом проблемы маркировки слов.
Основная проблема заключалась в том, что API сервера ожидает строковые ключи (word_id)
и числовые значения (translate_id). Если типы данных не соответствуют ожиданиям,
слова могут быть неправильно маркированы как "ошибленные".
"""

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


class LingualeoAPIClientFixed:
    """
    Улучшенная версия клиента для взаимодействия с API Lingualeo.
    Поддерживает синхронные и асинхронные запросы, управление cookies.
    Исправлена проблема с отправкой результатов тренировки.
    """

    def __init__(self, cookies: Optional[str] = None, user_id: Optional[int] = None):
        self.cookies = cookies or SAMPLE_COOKIES
        self.user_id = user_id
        self.headers = DEFAULT_HEADERS.copy()
        self.headers['Cookie'] = self.cookies
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.async_client = None
        self.logger = logging.getLogger(__name__)

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

    def process_training_answer_batch(self, training_results: dict) -> Dict:
        """
        Отправляет все результаты тренировки одним запросом (word_set_repetition).
        ИСПРАВЛЕНО: Гарантирует правильные типы данных для API.
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
        
        url = 'https://api.lingualeo.com/ProcessTraining'
        
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() 
                      for c in self.cookies.split(';') if '=' in c}
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
                self.logger.warning(f"Ошибка преобразования типов данных: word_id={word_id}, translate_id={translate_id}: {e}")
                # В случае ошибки преобразования, используем значения как есть
                normalized_results[str(word_id)] = translate_id
        
        # Логируем преобразование для отладки
        self.logger.debug(f"Оригинальные результаты: {training_results}")
        self.logger.debug(f"Нормализованные результаты: {normalized_results}")
        
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

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def process_training_answer_async(self, user_id: int, word_id: int, translate_id: int) -> Dict:
        """
        Асинхронно отправляет ответ на вопрос тренировки (word_set_repetition).
        ИСПРАВЛЕНО: Гарантирует правильные типы данных для API.
        """
        if not await self.load_user_cookies_async(user_id):
            raise ValueError("Cookies not found. Login first.")
            
        url = 'https://api.lingualeo.com/ProcessTraining'
        
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() 
                      for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        # ИСПРАВЛЕНИЕ: Убедимся, что word_id в строковом формате, а translate_id в числовом
        str_word_id = str(word_id)
        int_translate_id = int(translate_id)

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_set_repetition",
            "data": {
                "words": {str_word_id: int_translate_id},
                "wordSetId": 0
            },
            "iDs": [{"y": ym_uid}]
        }

        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    # Другие методы API-клиента остаются без изменений
    # Остальные методы можно скопировать из оригинального api_client.py

    def get_training_words_alternative(self):
        """
        Альтернативный метод получения слов для тренировки.
        """
        # Реализация такая же, как в оригинальном классе
        # ...

    def get_dictionary_words(self):
        """
        Получаем слова из словаря пользователя для тренировки.
        """
        # Реализация такая же, как в оригинальном классе
        # ...

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
        ИСПРАВЛЕНО: Гарантирует правильные типы данных для API.
        """
        if not self.load_cookies():
            raise ValueError("Cookies not found. Login first.")
            
        url = 'https://api.lingualeo.com/ProcessTraining'
        
        # Извлекаем ID из cookies
        cookies_dict = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() 
                      for c in self.cookies.split(';') if '=' in c}
        ym_uid = cookies_dict.get('_ym_uid') or cookies_dict.get('lingualeouid')
        if not ym_uid:
            raise ValueError("Не найден ни _ym_uid, ни lingualeouid в cookies.")

        # ИСПРАВЛЕНИЕ: Убедимся, что word_id в строковом формате, а translate_id в числовом
        str_word_id = str(word_id)
        int_translate_id = int(translate_id)

        payload = {
            "api_call": "process_training",
            "apiVersion": "1.0.1",
            "trainingName": "word_set_repetition",
            "data": {
                "words": {str_word_id: int_translate_id},
                "wordSetId": 0
            },
            "iDs": [{"y": ym_uid}]
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

# Функция для быстрого исправления существующего экземпляра LingualeoAPIClient
def fix_existing_process_training_answer_batch(client, training_results):
    """
    Исправленная версия process_training_answer_batch для применения к
    существующему экземпляру LingualeoAPIClient.
    
    Эта функция может быть использована как быстрый фикс без 
    необходимости полностью заменять API-клиент.
    
    Например:
    ```
    from api_client import LingualeoAPIClient
    from api_client_fixed import fix_existing_process_training_answer_batch
    
    client = LingualeoAPIClient()
    # Используем исправленную версию для отправки результатов
    response = fix_existing_process_training_answer_batch(client, training_results)
    ```
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