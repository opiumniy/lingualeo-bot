import sys
import os
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импортов
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Добавляем директорию lingualeo_pyth в путь
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Импортируем необходимые библиотеки
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Импортируем локальные модули с fallback для разных способов запуска
try:
    # Пробуем относительные импорты (если запущено как модуль)
    from . import keys
    from ..api_client import LingualeoAPIClient
    from ..config import get_user_cookies_path, get_global_cookies_path
except ImportError:
    try:
        # Пробуем абсолютные импорты из родительской директории
        import keys
        from api_client import LingualeoAPIClient
        from config import get_user_cookies_path, get_global_cookies_path
    except ImportError:
        # Fallback: добавляем текущую директорию в путь и пробуем снова
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))

        parent_dir = current_dir.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        import keys
        from api_client import LingualeoAPIClient
        from config import get_user_cookies_path, get_global_cookies_path

# Настройка логирования в файл
current_dir = Path(__file__).parent
logs_dir = current_dir / 'logs'
logs_dir.mkdir(exist_ok=True)

log_filename = f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = logs_dir / log_filename

# Создаем форматтер с более подробной информацией
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

# Настройка обработчиков
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Настройка корневого логгера
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=keys.token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний
class Form(StatesGroup):
    waiting_for_login = State()
    waiting_for_words = State()
    training_mode = State()
    waiting_for_answer = State()
    waiting_for_training_confirmation = State()
    waiting_for_server_send_confirmation = State()
    waiting_for_server_response_confirmation = State()
    waiting_for_final_confirmation = State()

def get_training_results_path(user_id: int) -> str:
    """Получает путь к файлу с результатами тренировки пользователя"""
    current_dir = Path(__file__).parent
    return str(current_dir / f"training_results_{user_id}.json")

def save_training_results(user_id: int, training_results: dict) -> bool:
    """Сохраняет результаты тренировки в локальный файл"""
    try:
        path = get_training_results_path(user_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Загружаем существующие результаты, если файл есть
        existing_results = {}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Файл результатов поврежден, создаем новый: {path}")

        # Объединяем с новыми результатами
        existing_results.update(training_results)

        # Сохраняем в файл
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing_results, f, ensure_ascii=False, indent=2)

        logger.info(f"Результаты тренировки сохранены локально: {len(training_results)} ответов для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов тренировки: {e}")
        return False

def load_training_results(user_id: int) -> dict:
    """Загружает результаты тренировки из локального файла"""
    try:
        path = get_training_results_path(user_id)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки результатов тренировки: {e}")
        return {}

async def _handle_wrong_answer(data: dict, word_index: int, selected_option: int, wrong_answers: list):
    """Обрабатывает неправильный ответ пользователя"""
    try:
        training_words = data.get('training_words', [])
        if word_index >= len(training_words):
            logger.warning(f"Индекс слова {word_index} выходит за границы массива")
            return

        current_word = training_words[word_index]
        current_word_data = training_words[word_index]

        # Получаем варианты ответов для текущего слова
        all_words = training_words.copy()
        other_words = [w for w in all_words if w != current_word_data]

        if not other_words:
            logger.warning("Нет других слов для создания вариантов ответа")
            return

        import random
        wrong_answers_sample = random.sample(other_words, min(3, len(other_words)))
        current_options = [current_word_data.get('correct_translate_value', '')] + \
                         [w.get('correct_translate_value', '') for w in wrong_answers_sample]
        random.shuffle(current_options)

        # Сохраняем информацию об ошибке
        wrong_answer_info = {
            'word': current_word.get('word_value', ''),
            'correct_translate': current_word.get('correct_translate_value', ''),
            'user_translate': current_options[selected_option] if selected_option < len(current_options) else 'Неизвестно'
        }

        wrong_answers.append(wrong_answer_info)
        logger.debug(f"Сохранена информация об ошибке: {wrong_answer_info}")

    except Exception as e:
        logger.error(f"Ошибка при обработке неправильного ответа: {e}")

def clear_training_results(user_id: int) -> tuple[bool, bool]:
    """Очищает файл с результатами тренировки

    Returns:
        tuple[bool, bool]: (успех_очистки, был_файл_до_очистки)
    """
    try:
        path = get_training_results_path(user_id)
        file_existed = os.path.exists(path)

        if file_existed:
            os.remove(path)
            logger.info(f"Файл результатов тренировки очищен: {path}")
        else:
            logger.info(f"Файл результатов тренировки не найден для очистки: {path}")

        return True, file_existed
    except Exception as e:
        logger.error(f"Ошибка очистки результатов тренировки: {e}")
        return False, False

def verify_cache_cleanup(user_id: int) -> dict:
    """Проверяет статус очистки кеша для пользователя

    Returns:
        dict: {
            'cache_cleared': bool,
            'file_existed_before': bool,
            'file_exists_after': bool,
            'cleanup_status': str
        }
    """
    try:
        path = get_training_results_path(user_id)

        # Проверяем текущее состояние файла
        file_exists_after = os.path.exists(path)

        # Определяем статус очистки
        if file_exists_after:
            cleanup_status = "❌ Кеш не очищен - файл все еще существует"
        else:
            cleanup_status = "✅ Кеш успешно очищен"

        return {
            'cache_cleared': not file_exists_after,
            'file_existed_before': True,  # Мы предполагаем, что файл был, так как вызываем очистку
            'file_exists_after': file_exists_after,
            'cleanup_status': cleanup_status
        }
    except Exception as e:
        logger.error(f"Ошибка проверки очистки кеша: {e}")
        return {
            'cache_cleared': False,
            'file_existed_before': False,
            'file_exists_after': True,
            'cleanup_status': f"❌ Ошибка проверки: {e}"
        }

def check_cache_status_before_training(user_id: int) -> dict:
    """Проверяет статус кеша перед началом тренировки

    Returns:
        dict: {
            'has_cache': bool,
            'cache_size': int,
            'cache_status': str
        }
    """
    try:
        path = get_training_results_path(user_id)

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cache_size = len(data)
                return {
                    'has_cache': True,
                    'cache_size': cache_size,
                    'cache_status': f"📋 Найден кеш с {cache_size} результатами тренировки"
                }
            except json.JSONDecodeError:
                return {
                    'has_cache': True,
                    'cache_size': 0,
                    'cache_status': "⚠️ Найден поврежденный файл кеша"
                }
        else:
            return {
                'has_cache': False,
                'cache_size': 0,
                'cache_status': "✅ Кеш пуст - готов к новой тренировке"
            }
    except Exception as e:
        logger.error(f"Ошибка проверки кеша перед тренировкой: {e}")
        return {
            'has_cache': False,
            'cache_size': 0,
            'cache_status': f"❌ Ошибка проверки кеша: {e}"
        }

@dp.message(Command("start"))
async def send_welcome(message: Message):
    commands = r"""
Доступные команды:
/start - Начать работу с ботом
/login - Войти в аккаунт Lingualeo
/addword - Добавить новое слово
/rep_engrus - Тренировка английских слов с русским переводом
/send_results - Отправить сохраненные результаты тренировки на сервер
    """
    await message.answer(commands)

@dp.message(Command("rep_engrus"))
async def start_training(message: Message, state: FSMContext):
    """Запуск тренировки английских слов с русским переводом"""
    logger.info(f"start_training вызвана пользователем {message.from_user.id}")

    try:
        # Проверяем аутентификацию пользователя
        logger.info(f"Проверка аутентификации для пользователя {message.from_user.id}")
        client = LingualeoAPIClient(user_id=message.from_user.id)

        if not await client.load_user_cookies_async(message.from_user.id):
            logger.warning(f"Не удалось загрузить cookies для пользователя {message.from_user.id}")
            await message.answer("❌ Сначала войдите в систему с помощью команды /login")
            return

        logger.info("Аутентификация успешна, заголовки обновлены")

        # Пробуем разные методы получения слов для тренировки
        training_data = None

        logger.info(f"Начинаем получение слов для тренировки пользователя {message.from_user.id}")

        try:
            # Сначала пробуем асинхронный метод
            logger.info("Пробуем асинхронный метод get_training_words_async")
            training_data = await client.get_training_words_async(message.from_user.id)
            logger.info(f"Асинхронный метод успешен, получено данных: {len(str(training_data))}")
        except Exception as e:
            logger.error(f"Асинхронный метод не сработал: {e}")
            try:
                # Если не получилось, пробуем альтернативный метод
                logger.info("Пробуем альтернативный метод get_training_words_alternative")
                alt_client = LingualeoAPIClient(user_id=message.from_user.id)
                if not alt_client.load_cookies(alt_client.user_id):
                    logger.error("Не удалось загрузить cookies для альтернативного метода")
                    await message.answer("Ошибка аутентификации. Попробуйте войти заново командой /login")
                    return
                training_data = alt_client.get_training_words_alternative()
                logger.info(f"Альтернативный метод успешен, получено данных: {len(str(training_data))}")
            except Exception as e2:
                logger.error(f"Альтернативный метод не сработал: {e2}")
                try:
                    # Если не получилось, пробуем получить слова из словаря
                    logger.info("Пробуем метод словаря get_dictionary_words")
                    dict_client = LingualeoAPIClient(user_id=message.from_user.id)
                    if not dict_client.load_cookies(dict_client.user_id):
                        logger.error("Не удалось загрузить cookies для метода словаря")
                        await message.answer("Ошибка аутентификации. Попробуйте войти заново командой /login")
                        return
                    training_data = dict_client.get_dictionary_words()
                    logger.info(f"Метод словаря успешен, получено данных: {len(str(training_data))}")
                except Exception as e3:
                    logger.error(f"Метод словаря не сработал: {e3}")
                    await message.answer("Ошибка получения данных для тренировки. Попробуйте войти в аккаунт заново командой /login")
                    return

        logger.info(f"Статус training_data: {training_data.get('status') if training_data else 'None'}")

        if not training_data or training_data.get('status') != 'ok':
            logger.error(f"Ошибка: training_data пустой или статус не ok: {training_data}")
            await message.answer("Ошибка получения данных для тренировки")
            return

        # Обрабатываем данные в зависимости от источника
        user_words = []

        logger.info(f"Обрабатываем training_data, ключи: {list(training_data.keys())}")

        if 'game' in training_data:
            # Данные из ProcessTraining API
            game_data = training_data.get('game', {})
            user_words = game_data.get('user_words', [])
            logger.info(f"Данные из ProcessTraining API: {len(user_words)} слов")
        elif 'data' in training_data:
            # Данные из GetWords API
            words_data = training_data.get('data', [])
            logger.info(f"Данные из GetWords API: {len(words_data)} слов")
            # Конвертируем формат GetWords в формат для тренировки
            for word in words_data[:10]:  # Берем первые 10 слов
                user_words.append({
                    'word_id': word.get('id', 0),
                    'word_value': word.get('word', ''),
                    'correct_translate_value': word.get('translate', ''),
                    'progress_percent': 50  # По умолчанию средний прогресс
                })
            logger.info(f"Конвертировано в формат тренировки: {len(user_words)} слов")

        logger.info(f"Финальное количество слов для тренировки: {len(user_words)}")

        if not user_words:
            logger.error("ОШИБКА: Нет слов для тренировки!")
            await message.answer("Нет слов для тренировки")
            return

        # Логируем информацию о первых нескольких словах
        for i, word in enumerate(user_words[:3]):
            logger.info(f"Слово {i+1}: {word.get('word_value')} -> {word.get('correct_translate_value')}, repeat_at: {word.get('repeat_at')}")

        # Загружаем существующие результаты тренировки, если есть
        existing_results = load_training_results(message.from_user.id)
        if existing_results:
            logger.info(f"Загружены существующие результаты тренировки: {len(existing_results)} ответов")
        else:
            logger.info("Новые результаты тренировки")

        # Сохраняем слова для тренировки в состояние
        await state.update_data(
            training_words=user_words,
            current_word_index=0,
            correct_answers=0,
            total_answers=0,
            wrong_answers=[],
            training_results=existing_results,
            user_id=message.from_user.id  # Сохраняем user_id в состоянии
        )
        await state.set_state(Form.training_mode)

        # Начинаем тренировку с первым словом
        await send_next_word(message, state, client)

    except Exception as e:
        logger.error(f"Ошибка при запуске тренировки: {str(e)}")
        await message.answer("Произошла ошибка при запуске тренировки. Попробуйте позже.")

@dp.message(Command("send_results"))
async def send_saved_results(message: Message):
    """Отправляет сохраненные результаты тренировки на сервер"""
    user_id = message.from_user.id
    logger.info(f"send_saved_results вызвана пользователем {user_id}")

    try:
        # Загружаем сохраненные результаты
        logger.info(f"Загружаем сохраненные результаты для пользователя {user_id}")
        training_results = load_training_results(user_id)

        if not training_results:
            logger.info(f"Нет сохраненных результатов для пользователя {user_id}")
            await message.answer("❌ У вас нет сохраненных результатов тренировки для отправки.")
            return

        logger.info(f"Найдено {len(training_results)} сохраненных результатов")
        await message.answer(f"📤 Найдено {len(training_results)} сохраненных результатов тренировки. Отправляем на сервер...")

        # Проверяем аутентификацию и отправляем результаты
        logger.info(f"Проверка аутентификации для отправки результатов пользователя {user_id}")
        client = LingualeoAPIClient(user_id=user_id)

        if not await client.load_user_cookies_async(user_id):
            logger.error(f"Не удалось загрузить cookies для пользователя {user_id}")
            await message.answer("❌ Не удалось загрузить cookies для отправки результатов. Попробуйте войти заново командой /login")
            return

        logger.info("Cookies загружены, отправляем результаты на сервер")
        try:
            # Отправляем результаты на сервер
            server_response = client.process_training_answer_batch(training_results)
            logger.info(f"Результаты успешно отправлены: {type(server_response)}")

            # Очищаем локальные результаты после успешной отправки
            cleanup_success, file_existed = clear_training_results(user_id)
            if cleanup_success:
                if file_existed:
                    logger.info(f"Локальные результаты очищены для пользователя {user_id}")
                    await message.answer(f"✅ Успешно отправлено {len(training_results)} результатов тренировки на сервер!")
                else:
                    logger.info(f"Файл результатов не найден для очистки пользователя {user_id}")
                    await message.answer(f"✅ Успешно отправлено {len(training_results)} результатов тренировки на сервер!")
            else:
                logger.warning(f"Не удалось очистить локальный файл для пользователя {user_id}")
                await message.answer(f"⚠️ Результаты отправлены, но не удалось очистить локальный файл")

        except Exception as api_error:
            logger.error(f"Ошибка API при отправке результатов для пользователя {user_id}: {api_error}")
            await message.answer("❌ Ошибка при отправке результатов на сервер. Проверьте подключение к интернету.")

    except FileNotFoundError as e:
        logger.error(f"Файл результатов не найден для пользователя {user_id}: {e}")
        await message.answer("❌ Файл с результатами не найден.")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка чтения JSON для пользователя {user_id}: {e}")
        await message.answer("❌ Ошибка чтения файла результатов.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке результатов для пользователя {user_id}: {e}")
        await message.answer("❌ Произошла неожиданная ошибка при отправке результатов. Попробуйте позже.")

@dp.message(Command("login"))
async def start_login(message: Message, state: FSMContext):
    logger.info("start_login вызвана")
    await message.answer("Отправь email и пароль через запятую (например: email,password).")
    await state.set_state(Form.waiting_for_login)

@dp.message(StateFilter(Form.waiting_for_login))
async def do_login(message: Message, state: FSMContext):
    """Обработка данных для входа в систему"""
    user_id = message.from_user.id
    logger.info(f"do_login вызвана пользователем {user_id}")

    try:
        # Парсим ввод пользователя
        user_input = message.text.split(',')
        if len(user_input) != 2:
            logger.warning(f"Неверный формат ввода от пользователя {user_id}: {message.text}")
            await message.answer("❌ Отправьте email и пароль через запятую (например: email@example.com,password)")
            return

        email, password = [u.strip() for u in user_input]
        logger.info(f"Попытка входа для пользователя {user_id} с email: {email[:3]}...")

        if not email or not password:
            logger.warning(f"Пустые credentials от пользователя {user_id}")
            await message.answer("❌ Email и пароль не могут быть пустыми")
            return

        # Выполняем вход
        client = LingualeoAPIClient(user_id=user_id)
        try:
            response = await client.login_async(email, password, user_id)

            if response and response.get('error_msg') == '':
                logger.info(f"Успешный логин для пользователя {user_id}")

                # Копируем cookies в глобальный файл для совместимости
                try:
                    user_path = get_user_cookies_path(user_id)
                    global_path = get_global_cookies_path()

                    if os.path.exists(user_path):
                        with open(user_path, 'r', encoding='utf-8') as src:
                            content = src.read().strip()
                        with open(global_path, 'w', encoding='utf-8') as dst:
                            dst.write(content)
                        logger.info(f"Cookies скопированы в глобальный файл {global_path}")
                except Exception as copy_error:
                    logger.warning(f"Не удалось скопировать cookies в глобальный файл: {copy_error}")

                await message.answer("✅ Логин успешен! Можете начинать тренировку командой /rep_engrus")
            else:
                error_msg = response.get('error_msg', 'Неизвестная ошибка') if response else 'Ошибка сервера'
                logger.warning(f"Ошибка логина для пользователя {user_id}: {error_msg}")
                await message.answer(f"❌ Ошибка входа: {error_msg}")

        except Exception as login_error:
            logger.error(f"Ошибка при выполнении логина для пользователя {user_id}: {login_error}")
            await message.answer("❌ Ошибка соединения с сервером. Проверьте интернет и попробуйте позже.")

        finally:
            await state.clear()

    except Exception as e:
        logger.error(f"Неожиданная ошибка в do_login для пользователя {user_id}: {e}")
        await message.answer("❌ Произошла неожиданная ошибка. Попробуйте позже.")
        await state.clear()

@dp.message(Command("addword"))
async def start_add_word(message: Message, state: FSMContext):
    logger.info("start_add_word вызвана")
    await message.answer("Отправь слово и перевод через запятую (например: word,translation).")
    await state.set_state(Form.waiting_for_words)

@dp.message(StateFilter(Form.waiting_for_words))
async def add_word(message: Message, state: FSMContext):
    try:
        logger.info("add_word вызвана")
        user_input = message.text.split(',')
        if len(user_input) == 2:
            word, translation = [u.strip() for u in user_input]
            client = LingualeoAPIClient(user_id=message.from_user.id)
            response_text = await client.add_word_async(word, translation, message.from_user.id)
            await message.answer(response_text)
            await state.clear()
        else:
            await message.answer('Отправь слово и перевод через запятую.')
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await message.answer("Произошла ошибка. Попробуй позже.")

async def send_next_word(message: Message, state: FSMContext, client: LingualeoAPIClient):
    """Отправляет следующее слово для тренировки"""
    data = await state.get_data()
    training_words = data.get('training_words', [])
    current_index = data.get('current_word_index', 0)

    if current_index >= len(training_words):
        # Тренировка завершена - начинаем пошаговый процесс
        await finish_training(message, state)
        return

    current_word = training_words[current_index]
    word_value = current_word.get('word_value', 'Неизвестное слово')
    correct_translate = current_word.get('correct_translate_value', '')

    # Получаем другие слова для вариантов ответа
    all_words = training_words.copy()
    other_words = [w for w in all_words if w != current_word]

    # Выбираем 3 случайных неправильных ответа
    import random
    wrong_answers = random.sample(other_words, min(3, len(other_words)))

    # Создаем варианты ответов
    options = [correct_translate] + [w.get('correct_translate_value', '') for w in wrong_answers]
    random.shuffle(options)

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{current_index}_{options.index(option)}")]
        for option in options
    ])

    # Сохраняем правильный ответ в состояние
    correct_option_index = options.index(correct_translate)
    # Получаем существующие результаты или создаем пустой словарь
    existing_results = data.get('training_results', {})

    await state.update_data(
        current_word_index=current_index,
        correct_option_index=correct_option_index,
        current_word_id=current_word.get('word_id'),
        training_results=existing_results
    )

    # Добавляем счетчик в формате (текущий\общий)
    total_words = len(training_words)
    counter_text = f"({current_index + 1}\\{total_words}) "

    await message.answer(
        f"{counter_text}Выберите перевод слова:\n\n🇬🇧 {word_value}",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('answer_'))
async def handle_training_answer(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает ответ пользователя в тренировке с улучшенной обработкой ошибок"""
    user_id = callback.from_user.id
    logger.info(f"handle_training_answer вызвана пользователем {user_id}")

    try:
        # Парсим callback data: answer_{word_index}_{selected_option_index}
        parts = callback.data.split('_')
        if len(parts) != 3:
            logger.error(f"Неверный формат callback_data от пользователя {user_id}: {callback.data}")
            await callback.answer("❌ Ошибка обработки ответа")
            return

        word_index = int(parts[1])
        selected_option = int(parts[2])
        logger.debug(f"Обработка ответа: word_index={word_index}, selected_option={selected_option}")

        # Получаем данные состояния
        data = await state.get_data()

        # Проверяем корректность данных
        if 'correct_option_index' not in data or 'current_word_id' not in data:
            logger.error(f"Недостаточно данных в состоянии для пользователя {user_id}")
            await callback.answer("❌ Ошибка состояния тренировки")
            return

        correct_option = data.get('correct_option_index', 0)
        current_word_id = data.get('current_word_id')

        # Определяем правильность ответа
        is_correct = selected_option == correct_option
        correct_answers = data.get('correct_answers', 0) + (1 if is_correct else 0)
        total_answers = data.get('total_answers', 0) + 1

        logger.info(f"Ответ пользователя {user_id}: правильный={is_correct}, word_id={current_word_id}")

        # Локально сохраняем результат ответа
        training_results = data.get('training_results', {})
        translate_id = 1 if is_correct else 2
        training_results[str(current_word_id)] = translate_id

        # Сохраняем результаты в файл (все накопленные результаты)
        if not save_training_results(user_id, training_results):
            logger.error(f"Ошибка сохранения результатов в файл для пользователя {user_id}")

        # Обрабатываем неправильный ответ
        wrong_answers = data.get('wrong_answers', [])
        if not is_correct:
            await _handle_wrong_answer(data, word_index, selected_option, wrong_answers)

        # Обновляем статистику в состоянии
        await state.update_data(
            correct_answers=correct_answers,
            total_answers=total_answers,
            current_word_index=word_index + 1,
            wrong_answers=wrong_answers,
            training_results=training_results
        )

        # Отправляем обратную связь пользователю
        if is_correct:
            await callback.answer("✅ Правильно!")
        else:
            await callback.answer("❌ Неправильно!")

        # Переходим к следующему слову
        client = LingualeoAPIClient(user_id=user_id)
        await send_next_word(callback.message, state, client)

    except ValueError as e:
        logger.error(f"Ошибка парсинга данных от пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка обработки ответа")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке ответа пользователя {user_id}: {e}")
        await callback.message.answer("❌ Произошла ошибка при обработке ответа. Попробуйте снова.")

async def finish_training(message: Message, state: FSMContext):
    """Автоматически завершает тренировку и отправляет результаты"""
    data = await state.get_data()
    correct_answers = data.get('correct_answers', 0)
    total_answers = data.get('total_answers', 0)
    wrong_answers = data.get('wrong_answers', [])
    training_words = data.get('training_words', [])
    training_results = data.get('training_results', {})

    accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0

    logger.info(f"Локальные результаты тренировки: {len(training_results)} ответов")

    # Автоматически отправляем результаты на сервер
    server_send_success = False
    server_response = None
    client = None
    cache_cleanup_info = None

    try:
        # Получаем user_id из состояния тренировки
        data = await state.get_data()
        user_id = data.get('user_id', message.from_user.id)  # Fallback на message.from_user.id
        logger.info(f"Попытка отправки результатов на сервер для пользователя {user_id}")

        client = LingualeoAPIClient(user_id=user_id)
        if await client.load_user_cookies_async(user_id):
            # Отправляем результаты на сервер
            server_response = client.process_training_answer_batch(training_results)

            if server_response and server_response.get('status') == 'ok':
                server_send_success = True
                logger.info("Результаты успешно отправлены на сервер")

                # Очищаем локальные результаты ТОЛЬКО после успешной отправки на сервер
                cleanup_success, file_existed = clear_training_results(user_id)

                # Проверяем реальное состояние кеша ПОСЛЕ очистки
                file_exists_after_cleanup = os.path.exists(get_training_results_path(user_id))

                if cleanup_success:
                    if file_existed and not file_exists_after_cleanup:
                        # Файл существовал и был успешно удален
                        logger.info("Локальные результаты тренировки очищены после успешной отправки")
                        cache_cleanup_info = {
                            'cache_cleared': True,
                            'file_existed_before': True,
                            'file_exists_after': False,
                            'cleanup_status': "✅ Кеш успешно очищен после успешной отправки"
                        }
                    elif not file_existed and not file_exists_after_cleanup:
                        # Файл не существовал и не существует (кеш был пуст)
                        logger.info("Файл результатов тренировки не найден для очистки")
                        cache_cleanup_info = {
                            'cache_cleared': True,
                            'file_existed_before': False,
                            'file_exists_after': False,
                            'cleanup_status': "✅ Кеш был пуст - нет данных для очистки"
                        }
                    else:
                        # Неожиданное состояние
                        logger.warning(f"Неожиданное состояние кеша: existed={file_existed}, exists_after={file_exists_after_cleanup}")
                        cache_cleanup_info = {
                            'cache_cleared': False,
                            'file_existed_before': file_existed,
                            'file_exists_after': file_exists_after_cleanup,
                            'cleanup_status': "⚠️ Неожиданное состояние кеша после очистки"
                        }
                else:
                    logger.error("Не удалось очистить локальные результаты тренировки")
                    cache_cleanup_info = {
                        'cache_cleared': False,
                        'file_existed_before': False,
                        'file_exists_after': True,
                        'cleanup_status': "❌ Ошибка очистки кеша после отправки"
                    }
            else:
                logger.error(f"Ошибка отправки на сервер: {server_response}")
                cache_cleanup_info = {
                    'cache_cleared': False,
                    'file_existed_before': True,
                    'file_exists_after': True,
                    'cleanup_status': "❌ Кеш не очищен - ошибка отправки на сервер"
                }
        else:
            logger.error("Не удалось загрузить cookies для отправки результатов")
            cache_cleanup_info = {
                'cache_cleared': False,
                'file_existed_before': True,
                'file_exists_after': True,
                'cleanup_status': "❌ Кеш не очищен - ошибка аутентификации"
            }
    except Exception as e:
        logger.error(f"Ошибка отправки результатов на сервер: {e}")
        cache_cleanup_info = {
            'cache_cleared': False,
            'file_existed_before': True,
            'file_exists_after': True,
            'cleanup_status': f"❌ Кеш не очищен - ошибка сервера: {e}"
        }

    # Показываем финальную статистику с интервалами
    await show_final_statistics(message, state, server_send_success, server_response, cache_cleanup_info)

async def show_final_statistics(message: Message, state: FSMContext, server_send_success: bool, server_response: dict, cache_cleanup_info: dict = None):
    """Показывает финальную статистику с интервалами в одном сообщении"""
    data = await state.get_data()
    correct_answers = data.get('correct_answers', 0)
    total_answers = data.get('total_answers', 0)
    wrong_answers = data.get('wrong_answers', [])
    training_words = data.get('training_words', [])
    accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0

    # Создаем финальное сообщение
    result_text = f"""🎯 FINAL STATISTICS:

📊 Training results:
✅ Correct answers: {correct_answers}
❌ Incorrect answers: {total_answers - correct_answers}
📈 Accuracy: {accuracy:.1f}%

❌ Mistakes in this training:
"""

    for wrong in wrong_answers:
        result_text += f"• {wrong['word']} — {wrong['correct_translate']}\n"

    result_text += f"\n{'🎉 Excellent result!' if accuracy >= 80 else '💪 Well done! Keep training!' if accuracy >= 60 else '📚 Recommended to repeat difficult words!'}\n\n"

    # Добавляем информацию об очистке кеша
    if cache_cleanup_info:
        result_text += f"🧹 CACHE CLEANUP STATUS:\n"
        result_text += f"{cache_cleanup_info.get('cleanup_status', '❌ Статус очистки неизвестен')}\n\n"
    else:
        result_text += f"🧹 CACHE CLEANUP STATUS:\n"
        result_text += f"❌ Информация об очистке кеша недоступна\n\n"

    # Добавляем интервалы повторения
    if server_send_success and server_response and 'words' in server_response and server_response['words']:
        server_words = server_response['words']
        server_words_dict = {}
        for server_word in server_words:
            word_id = str(server_word.get('word_id', ''))
            server_words_dict[word_id] = server_word

        result_text += "REVIEW INTERVALS:\n\n"
        found_words = 0

        for word in training_words:
            word_id = str(word.get('word_id', ''))
            word_value = word.get('word_value', 'неизвестное слово')
            translate_value = word.get('correct_translate_value', '')

            server_word_data = server_words_dict.get(word_id)
            if server_word_data:
                repeat_at = server_word_data.get('repeat_at', '')
                repeat_interval = server_word_data.get('repeat_interval', 480)
                interval_text = calculate_next_repetition(repeat_at, repeat_interval)
                result_text += f"• {word_value} — {translate_value}: {interval_text}\n"
                found_words += 1

        result_text += f"\n✅ Words with intervals found: {found_words} out of {len(training_words)}"
    else:
        result_text += "\n❌ Could not get intervals from server"

    await message.answer(result_text)
    await state.clear()

@dp.callback_query(lambda c: c.data in ['confirm_training_end', 'cancel_training_end'])
async def handle_training_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение завершения тренировки"""
    if callback.data == 'cancel_training_end':
        await callback.message.answer("❌ Отправка результатов отменена")
        await state.clear()
        await callback.answer()
        return

    await callback.message.answer("📤 Готовлю данные для отправки на сервер...")
    await callback.answer()

    # Переходим к следующему шагу - отправка на сервер
    await state.set_state(Form.waiting_for_server_send_confirmation)

    # Получаем данные из состояния
    data = await state.get_data()
    training_results = data.get('training_results', {})

    # Показываем запрос который будем отправлять (разбиваем если слишком длинный)
    request_json = json.dumps(training_results, ensure_ascii=False, indent=2)
    max_length = 4000

    if len(request_json) > max_length:
        # Разбиваем на несколько сообщений
        parts = []
        for i in range(0, len(request_json), max_length):
            parts.append(request_json[i:i + max_length])

        for part in parts[:-1]:
            await callback.message.answer(f"```\n{part}\n```")

        request_text = f"""
📨 ЗАПРОС НА СЕРВЕР (часть {len(parts)}):
POST /ProcessTraining
Данные: {parts[-1]}

Готовы отправить этот запрос на сервер Lingualeo?
"""
    else:
        request_text = f"""
📨 ЗАПРОС НА СЕРВЕР:
POST /ProcessTraining
Данные: {request_json}

Готовы отправить этот запрос на сервер Lingualeo?
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОТПРАВИТЬ", callback_data="send_to_server")],
        [InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="cancel_send")]
    ])

    await callback.message.answer(request_text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data in ['send_to_server', 'cancel_send'])
async def handle_server_send(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает отправку данных на сервер"""
    if callback.data == 'cancel_send':
        await callback.message.answer("❌ Отправка отменена")
        await state.clear()
        await callback.answer()
        return

    await callback.message.answer("⏳ Отправляю данные на сервер Lingualeo...")
    await callback.answer()

    # Получаем данные из состояния
    data = await state.get_data()
    training_results = data.get('training_results', {})

    # Отправляем данные на сервер
    try:
        client = LingualeoAPIClient(user_id=callback.from_user.id)
        if not await client.load_user_cookies_async(callback.from_user.id):
            await callback.message.answer("❌ Не удалось загрузить cookies для отправки")
            await state.clear()
            return

        # Отправляем результаты на сервер
        server_response = client.process_training_answer_batch(training_results)

        # Сохраняем ответ сервера в состояние
        await state.update_data(server_response=server_response)

        # Показываем ответ сервера (разбиваем на части если слишком длинный)
        response_json = json.dumps(server_response, ensure_ascii=False, indent=2)
        max_length = 4000  # Максимальная длина сообщения в Telegram

        if len(response_json) > max_length:
            # Разбиваем на несколько сообщений
            parts = []
            for i in range(0, len(response_json), max_length):
                parts.append(response_json[i:i + max_length])

            for part in parts[:-1]:
                await callback.message.answer(f"```\n{part}\n```")

            response_text = f"""
📨 ОТВЕТ СЕРВЕРА (часть {len(parts)}):
{parts[-1]}

Готовы продолжить?
"""
        else:
            response_text = f"""
📨 ОТВЕТ СЕРВЕРА:
{response_json}

Готовы продолжить?
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ ПРОДОЛЖИТЬ", callback_data="confirm_cleanup")],
            [InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="cancel_process")]
        ])

        await state.set_state(Form.waiting_for_server_response_confirmation)
        await callback.message.answer(response_text, reply_markup=keyboard)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка отправки на сервер: {e}")
        await state.clear()

@dp.callback_query(lambda c: c.data in ['confirm_cleanup', 'cancel_process'])
async def handle_cleanup_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение очистки результатов"""
    if callback.data == 'cancel_process':
        await callback.message.answer("❌ Процесс отменен")
        await state.clear()
        await callback.answer()
        return

    await callback.message.answer("🧹 Очищаю локальные результаты тренировки...")
    await callback.answer()

    # Очищаем локальные результаты
    cleanup_success, file_existed = clear_training_results(callback.from_user.id)
    if cleanup_success:
        if file_existed:
            await callback.message.answer("✅ Локальные результаты успешно очищены!\n\nТеперь можно продолжить с расчетом интервалов.")
        else:
            await callback.message.answer("✅ Локальные результаты уже были пусты!\n\nТеперь можно продолжить с расчетом интервалов.")
    else:
        await callback.message.answer("⚠️ Не удалось очистить локальные результаты")

    # Переходим к следующему шагу - расчет интервалов
    await state.set_state(Form.waiting_for_server_response_confirmation)

    # Получаем данные из состояния
    data = await state.get_data()
    server_response = data.get('server_response', {})
    training_words = data.get('training_words', [])

    # Рассчитываем интервалы на основе ответа сервера
    intervals_text = "ИНТЕРВАЛЫ ПОВТОРЕНИЯ:\n\n"

    if server_response and 'words' in server_response and server_response['words']:
        server_words = server_response['words']

        # Создаем словарь для быстрого поиска по word_id
        server_words_dict = {}
        for server_word in server_words:
            word_id = str(server_word.get('word_id', ''))
            server_words_dict[word_id] = server_word

        found_words = 0
        for word in training_words:
            word_id = str(word.get('word_id', ''))
            word_value = word.get('word_value', 'неизвестное слово')
            translate_value = word.get('correct_translate_value', '')

            # Ищем данные слова в ответе сервера
            server_word_data = server_words_dict.get(word_id)

            if server_word_data:
                repeat_at = server_word_data.get('repeat_at', '')
                repeat_interval = server_word_data.get('repeat_interval', 480)

                # Рассчитываем интервал
                interval_text = calculate_next_repetition(repeat_at, repeat_interval)
                intervals_text += f"• {word_value} — {translate_value}: {interval_text}\n"
                found_words += 1
            else:
                intervals_text += f"• {word_value} — {translate_value}: dannye ne naydeny\n"

        if found_words == 0:
            intervals_text += "\n❌ Ни одно слово не найдено в ответе сервера\n"
        else:
            intervals_text += f"\n✅ Найдено слов с интервалами: {found_words} из {len(training_words)}\n"
    else:
        intervals_text += "❌ Данные об интервалах не получены от сервера\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПОКАЗАТЬ СТАТИСТИКУ", callback_data="show_final_stats")],
        [InlineKeyboardButton(text="❌ ЗАКОНЧИТЬ", callback_data="finish_session")]
    ])

    await state.set_state(Form.waiting_for_final_confirmation)
    await callback.message.answer(intervals_text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data in ['show_final_stats', 'finish_session'])
async def handle_final_confirmation(callback: CallbackQuery, state: FSMContext):
    """Показывает финальную статистику или завершает сессию"""
    if callback.data == 'finish_session':
        await callback.message.answer("✅ Сессия завершена")
        await state.clear()
        await callback.answer()
        return

    # Показываем финальную статистику
    data = await state.get_data()
    correct_answers = data.get('correct_answers', 0)
    total_answers = data.get('total_answers', 0)
    wrong_answers = data.get('wrong_answers', [])
    accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0

    result_text = f"""
🎯 ФИНАЛЬНАЯ СТАТИСТИКА:

📊 Результаты тренировки:
✅ Правильных ответов: {correct_answers}
❌ Неправильных ответов: {total_answers - correct_answers}
📈 Точность: {accuracy:.1f}%

❌ Ошибки в этой тренировке:
"""
    for wrong in wrong_answers:
        result_text += f"• {wrong['word']} — {wrong['correct_translate']}\n"

    result_text += f"\n{'🎉 Отличный результат!' if accuracy >= 80 else '💪 Хорошо! Продолжайте тренироваться!' if accuracy >= 60 else '📚 Рекомендуем повторить сложные слова!'}"

    await callback.message.answer(result_text)
    await state.clear()
    await callback.answer()

def calculate_next_repetition(repeat_at, repeat_interval):
    """Рассчитывает следующий интервал повторения"""
    import datetime

    if not repeat_at or repeat_at == "0000-00-00 00:00:00+00":
        # Используем repeat_interval для расчета
        try:
            minutes = int(float(repeat_interval or 480))
            if minutes >= 1440:  # 24 часа
                days = minutes // 1440
                return f"↑ {days} д."
            elif minutes >= 480:  # 8 часов
                hours = minutes // 60
                return f"↓ {hours} ч."
            else:
                return "↓ 6 ч."
        except (ValueError, TypeError):
            return "↓ 8 ч."
    else:
        # Рассчитываем по дате
        try:
            if '+' in repeat_at:
                repeat_at = repeat_at.replace('+00', '+00:00')
            elif repeat_at.endswith('+00'):
                repeat_at = repeat_at[:-3] + '+00:00'

            repeat_date = datetime.datetime.fromisoformat(repeat_at.replace('Z', '+00:00'))
            now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            time_diff = repeat_date - now

            if time_diff.total_seconds() <= 0:
                return "↓ 6 ч."

            days = time_diff.days
            hours = time_diff.seconds // 3600

            if days >= 1:
                return f"↑ {days} д."
            elif hours >= 1:
                return f"↓ {hours} ч."
            else:
                return "↓ 6 ч."

        except Exception:
            return "↓ 8 ч."

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
