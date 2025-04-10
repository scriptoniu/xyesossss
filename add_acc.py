import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'

# Убедимся, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# Убедимся, что файл sessions.txt существует
if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w') as f:
        pass  # Просто создаем пустой файл, если его нет

# Функция для добавления аккаунта в sessions.txt
def add_account_to_file(phone):
    """Добавляет номер телефона в sessions.txt, если его нет"""
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    # Удаляем дубликаты: если номер уже есть, удаляем его
    lines = [line.strip() for line in lines if line.strip() != phone]

    # Добавляем новый номер в конец файла
    lines.append(phone)

    # Записываем обновленный список обратно в файл
    with open(SESSIONS_FILE, "w") as f:
        for line in lines:
            f.write(line + "\n")

# Добавление аккаунта
while True:
    phone = input("\nВведи номер телефона (или q для выхода): ")
    if phone.lower() == "q":
        break

    # Проверка на существование сессии для этого номера
    session_name = os.path.join(SESSION_DIR, phone.replace("+", "").replace(" ", ""))
    
    # Проверка на существование файла сессии
    if os.path.exists(session_name + '.session'):
        print(f"❌ Сессия для {phone} уже существует.")
        continue  # Пропустить добавление, если сессия уже есть

    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        client.connect()

        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input("Введи код из Telegram: ")
            client.sign_in(phone, code)

            # Проверка на необходимость двухфакторной аутентификации
            if client.is_user_authorized():
                print(f"✅ Сессия сохранена: {session_name}.session")
                # Добавляем номер в sessions.txt (удаляется если уже есть)
                add_account_to_file(phone)
                print("✅ Номер успешно добавлен в sessions.txt")
            else:
                print("❌ Ошибка авторизации")
                break
        else:
            print(f"✅ Клиент уже авторизован: {phone}")

    except SessionPasswordNeededError:
        # Это ошибка при двухфакторной аутентификации
        password = input(f"Введи код 2FA для номера {phone}: ")
        client.start(password=password)  # Пытаемся войти с 2FA

        if client.is_user_authorized():
            print(f"✅ Сессия сохранена: {session_name}.session")
            # Добавляем номер в sessions.txt (удаляется если уже есть)
            add_account_to_file(phone)
            print("✅ Номер успешно добавлен в sessions.txt")
        else:
            print("❌ Ошибка авторизации с 2FA")
            break
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        client.disconnect()