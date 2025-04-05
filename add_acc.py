from telethon.sync import TelegramClient
import os

API_ID = 25293202     # Замени на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Замени на свой API HASH

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'

# Убедимся, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

while True:
    phone = input("\nВведи номер телефона (или q для выхода): ")
    if phone.lower() == "q":
        break

    # Используем путь к файлу сессии внутри папки sessions
    session_name = os.path.join(SESSION_DIR, phone.replace("+", "").replace(" ", ""))
    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input("Введи код из Telegram: ")
            client.sign_in(phone, code)

            # Проверяем успешность авторизации перед сохранением
            if client.is_user_authorized():
                print(f"Сессия сохранена: {session_name}.session")
                # Открываем файл в режиме чтения, чтобы проверить наличие номера
                if not os.path.exists("sessions.txt"):
                    with open("sessions.txt", "w") as f:
                        f.write(phone + "\n")
                else:
                    with open("sessions.txt", "r") as f:
                        numbers = f.read().splitlines()
                    if phone not in numbers:
                        with open("sessions.txt", "a") as f:
                            f.write(phone + "\n")
                print("Номер успешно добавлен в sessions.txt")
            else:
                print("Ошибка авторизации")
        else:
            print(f"Клиент уже авторизован: {phone}")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        client.disconnect()