import asyncio
import os
import subprocess
import sys

SRC_DIR = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, SRC_DIR)


def check_env_file():
    if not os.path.exists('.env'):
        print("Ошибка: .env файл не найден!")
        print("Создайте .env файл с необходимыми переменными окружения")
        return False
    return True


def install_requirements():
    try:
        print("Устанавливаю зависимости...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Зависимости установлены успешно")
        return True
    except subprocess.CalledProcessError:
        print("Ошибка при установке зависимостей")
        return False


async def run_bot():
    try:
        print("Запускаю телеграм бота...")
        from tg_bot import main as bot_main
        await bot_main()
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f" Ошибка при запуске бота: {e}")
        return False
    return True


def main():
    print("Запуск агента...")

    if not check_env_file():
        return

    if not install_requirements():
        return

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)




if __name__ == "__main__":
    main()
