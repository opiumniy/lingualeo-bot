import subprocess
import sys
import importlib.util
from pathlib import Path

def check_dependencies():
    """
    Проверяет и устанавливает зависимости из requirements.txt.
    """
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("requirements.txt не найден. Установите зависимости вручную: pip install -r requirements.txt")
        return False
    
    # Ключевые модули для проверки
    required_modules = {
        'requests': 'requests',
        'pandas': 'pandas',
        'httpx': 'httpx',
        'aiofiles': 'aiofiles',
        'aiogram': 'aiogram',
        'curl_cffi': 'curl_cffi'
    }
    
    missing = []
    for module_name, package in required_modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package)
    
    if missing:
        print(f"Отсутствуют пакеты: {', '.join(missing)}")
        print("Устанавливаю зависимости...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("Зависимости установлены успешно!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Ошибка установки зависимостей: {e}")
            print("Установите вручную: pip install -r requirements.txt")
            return False
    else:
        print("Все зависимости установлены.")
        return True

def ensure_requirements():
    """
    Вызывает проверку зависимостей и выходит, если не удалось.
    """
    if not check_dependencies():
        input("Нажмите Enter для выхода...")
        sys.exit(1)