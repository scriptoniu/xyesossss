import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

# Словарь для хранения ID сообщений: {source_message_id: {target_chat_id: target_message_id}}
message_map = {}

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'

# Убедитесь, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# Функция для добавления аккаунта в sessions.txt
def add_account_to_file(phone):
    # Читаем текущие данные из файла
    if os.path.exists("sessions.txt"):
        with open("sessions.txt", "r") as f:
            lines = f.readlines()
    else:
        lines = []

    # Удаляем дубликаты: если номер уже есть, удаляем его
    lines = [line.strip() for line in lines if line.strip() != phone]

    # Добавляем новый номер в конец файла
    lines.append(phone)

    # Записываем обновленный список обратно в файл
    with open("sessions.txt", "w") as f:
        for line in lines:
            f.write(line + "\n")


# Асинхронная функция для обработки добавления аккаунта
async def add_account(phone):
    session_name = os.path.join(SESSION_DIR, phone.replace("+", "").replace(" ", ""))
    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        # Подключаемся к клиенту и ждем авторизации
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("Введи код из Telegram: ")
            await client.sign_in(phone, code)

            # Проверка на необходимость двухфакторной аутентификации
            if await client.is_user_authorized():
                print(f"Сессия сохранена: {session_name}.session")
                # Добавляем номер в sessions.txt (удаляется если уже есть)
                add_account_to_file(phone)
                print("Номер успешно добавлен в sessions.txt")
            else:
                print("Ошибка авторизации")
        else:
            print(f"Клиент уже авторизован: {phone}")

    except SessionPasswordNeededError:
        # Это ошибка при двухфакторной аутентификации
        password = input(f"Введи код 2FA для номера {phone}: ")
        await client.start(password=password)  # Пытаемся войти с 2FA

        if await client.is_user_authorized():
            print(f"Сессия сохранена: {session_name}.session")
            # Добавляем номер в sessions.txt (удаляется если уже есть)
            add_account_to_file(phone)
            print("Номер успешно добавлен в sessions.txt")
        else:
            print("Ошибка авторизации с 2FA")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await client.disconnect()

# Главная функция для ввода номера
async def main():
    while True:
        phone = input("\nВведи номер телефона (или q для выхода): ")
        if phone.lower() == "q":
            break

        await add_account(phone)

# Запуск программы
if __name__ == "__main__":
    asyncio.run(main())