import os

# API URLs
API_URLS = {
    'auth': 'https://lingualeo.com/api/auth',
    'set_words': 'https://api.lingualeo.com/SetWords',
    'load_words': 'https://api.lingualeo.com/SetWords',  # Для экспорта слов
}

# Общие заголовки для запросов
DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Content-Type': 'application/json',
    'Origin': 'https://lingualeo.com',
    'Referer': 'https://lingualeo.com/ru/dictionary/vocabulary/my',
    'Sec-Ch-Ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'DNT': '1',
}

# Директории для cookies
USER_COOKIES_DIR = 'User_Cookies'
GLOBAL_COOKIES_FILE = 'cookies_current.txt'  # Для не-TG скриптов

# Шаблоны payload
PAYLOAD_TEMPLATES = {
    'add_word': {
        'apiVersion': '1.0.1',
        'op': 'actionWithWords {action: add}',
        'data': [
            {
                'action': 'add',
                'mode': '0',
                'wordIds': None,
                'valueList': {
                    'wordSetId': 1,
                    'wordValue': None,
                    'translation': {
                        'id': 0,
                        'tr': None,
                        'main': 1,
                        'selected': 1
                    }
                }
            }
        ],
        'userData': {
            'nativeLanguage': 'lang_id_src'
        },
        'iDs': [
            {
                'y': '1684752513711783236',  # Заменить на актуальное из cookies
                'g': '1018540351.1695370975'
            }
        ]
    },
    'login': {
        'type': 'mixed',
        'credentials': {
            'email': None,
            'password': None
        }
    },
    'load_words': {
        'apiVersion': '1.0.1',
        'op': 'loadCompactWords',
        'data': [
            {
                'action': 'update',
                'mode': 'compact',
                'wordSetId': 1,
                'wordIds': None,
                'dateGroups': ['all']
            }
        ],
        'iDs': []  # Заполняется динамически из cookies
    }
}

# Функция для получения пути к cookies файла пользователя (для TG бота)
def get_user_cookies_path(user_id):
    os.makedirs(USER_COOKIES_DIR, exist_ok=True)
    return os.path.join(USER_COOKIES_DIR, f'{user_id}_cookies.txt')

# Функция для глобального cookies пути
def get_global_cookies_path():
    return GLOBAL_COOKIES_FILE

# Пример cookies строки (заменить на актуальную)
SAMPLE_COOKIES = '_ym_uid=1731927216910223507; _ym_d=1758474485; tmr_lvid=31559846206384e457309e14d672a9aa; tmr_lvidTS=1731927212432; remember=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOjExMzg5NzE1LCJleHAiOjE3NjY1MDk3MDIsInR5cCI6ImEifQ.LcaJVzj-jjDw_A2NQtb0CskdghqlPlOekLYFywq1g1Y; userid=11389715; _ym_isad=1'

# ID пользователя (из cookies)
SAMPLE_USER_ID = '11389715'