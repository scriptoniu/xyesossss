from telethon.sync import TelegramClient
import os

API_ID = 25293202  # Замени на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Замени на свой API HASH

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'

# Убедимся, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

def check_account_exists(phone_number):
    """
    Проверяет, существует ли аккаунт в Telegram.
    """
    session_name = os.path.join(SESSION_DIR, phone_number.replace("+", "").replace(" ", ""))
    if not os.path.exists(session_name + ".session"):
        print(f"Сессия для {phone_number} не найдена.")
        return False

    try:
        with TelegramClient(session_name, API_ID, API_HASH) as client:
            client.connect()
            if client.is_user_authorized():
                print(f"Аккаунт {phone_number} существует.")
                return True
            else:
                print(f"Аккаунт {phone_number} не авторизован.")
                return False
    except Exception as e:
        print(f"Ошибка при проверке аккаунта {phone_number}: {e}")
        return False


def remove_non_existing_accounts():
    """
    Удаляет несуществующие аккаунты из sessions.txt.
    """
    with open("sessions.txt", "r") as f:
        sessions = f.readlines()

    # Фильтруем только существующие аккаунты
    existing_sessions = []
    for session in sessions:
        session = session.strip()
        if check_account_exists(session):
            existing_sessions.append(session)
        else:
            print(f"Аккаунт {session} удалён, так как он не существует в Telegram.")

    # Перезаписываем файл sessions.txt
    with open("sessions.txt", "w") as f:
        for session in existing_sessions:
            f.write(session + "\n")
    
    print("Список аккаунтов обновлён.")


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

            # Если требуется двухфакторная аутентификация
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

        # Если требуется двухфакторная аутентификация (2FA)
        if not client.is_user_authorized():
            # Запрашиваем двухфакторный пароль
            two_fa_password = input("Введите двухфакторный пароль: ")
            try:
                client.check_password(two_fa_password)
                print("2FA авторизация прошла успешно.")
            except Exception as e:
                print(f"Ошибка при проверке 2FA пароля: {e}")
                continue
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        client.disconnect()

# Вызываем функцию удаления несуществующих аккаунтов после добавления новых
remove_non_existing_accounts()