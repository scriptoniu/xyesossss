from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError
import os

API_ID = 25293202  # Замени на свой API ID
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
            # Если сессия не авторизована, отправляем запрос на код
            client.send_code_request(phone)
            code = input("Введи код из Telegram: ")
            client.sign_in(phone, code)

            # Если включена 2FA, нужно ввести еще один код
            if client.is_user_authorized():
                try:
                    # Проверяем, если 2FA включена
                    client.start(phone, code)
                except SessionPasswordNeededError:
                    # Запросим код 2FA
                    password = input("Введи код 2FA: ")
                    client.start(password=password)

                print(f"Сессия сохранена: {session_name}.session")
                # Открываем файл в режиме чтения, чтобы проверить наличие номера
                if not os.path.exists("sessions.txt"):
                    with open("sessions.txt", "w") as f:
                        f.write(phone + "\n")  # Записываем номер в новый файл с новой строки
                else:
                    with open("sessions.txt", "r") as f:
                        numbers = f.read().splitlines()
                    if phone not in numbers:
                        with open("sessions.txt", "a") as f:
                            f.write(phone + "\n")  # Добавляем новый номер с новой строки
                print("Номер успешно добавлен в sessions.txt")
            else:
                print("Ошибка авторизации")
        else:
            print(f"Клиент уже авторизован: {phone}")
    
    except (PhoneCodeExpiredError, Exception) as e:
        # Если код устарел или сессия повреждена
        print(f"Ошибка с сессией или кодом: {e}")
        
        # Удаляем битую сессию
        if os.path.exists(session_name + ".session"):
            os.remove(session_name + ".session")
            print(f"Удалена поврежденная сессия: {session_name}.session")
        
        # Повторный запрос для создания новой сессии
        print("Попробуй снова войти с новым кодом.")
        
    except SessionPasswordNeededError:
        print("Необходим код 2FA для авторизации на этом аккаунте.")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
    finally:
        client.disconnect()