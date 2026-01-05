import os
import sys
import subprocess
from utils import ensure_requirements

ensure_requirements()

# Функция для запуска скрипта
def run_script(script_path, use_new_window=False):
    if not os.path.exists(script_path):
        print(f"Файл {script_path} не найден.")
        return
    
    try:
        if use_new_window and sys.platform == "win32":
            # На Windows открываем в новом окне
            subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            print(f"Скрипт {script_path} запущен в новом окне.")
        else:
            # Обычный запуск
            subprocess.call([sys.executable, script_path])
    except Exception as e:
        print(f"Ошибка запуска {script_path}: {e}")

# Главное меню
def main_menu():
    while True:
        print("\n=== Lingualeo Bot Launcher ===")
        print("1. Запустить Telegram бота (в новом окне)")
        print("2. Выгрузить слова из Lingualeo (parser)")
        print("3. Тренировка слов (trainer)")
        print("4. Bulk добавление слов из CSV")
        print("5. Выход")
        
        choice = input("Выберите опцию (1-5): ").strip()
        
        if choice == '1':
            run_script("lingualeo_pyth/tg_bot.py", use_new_window=True)
        elif choice == '2':
            run_script("lingua_leo_RU_EN/lingualeo_ultimate_parser.py")
        elif choice == '3':
            run_script("lingua_leo_RU_EN/trainer.py")
        elif choice == '4':
            run_script("bulk add/bot.py")
        elif choice == '5':
            print("До свидания!")
            break
        else:
            print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main_menu()