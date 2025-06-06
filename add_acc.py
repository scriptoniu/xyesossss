import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

API_ID = 25293202  # Замените на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Замените на свой API HASH

SESSION_DIR = 'sessions'

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

def add_account_to_file(phone):
    if os.path.exists("sessions.txt"):
        with open("sessions.txt", "r") as f:
            lines = f.readlines()
    else:
        lines = []

    lines = [line.strip() for line in lines if line.strip() != phone]
    lines.append(phone)

    with open("sessions.txt", "w") as f:
        for line in lines:
            f.write(line + "\n")

async def add_account(phone):
    session_name = os.path.join(SESSION_DIR, phone.replace("+", "").replace(" ", ""))
    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input(f"Введи код из Telegram для {phone}: ")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input(f"Введи пароль 2FA для {phone}: ")
                await client.sign_in(password=password)

        if await client.is_user_authorized():
            print(f"Сессия сохранена: {session_name}.session")
            add_account_to_file(phone)
            print("Номер успешно добавлен в sessions.txt")
        else:
            print("Ошибка авторизации")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await client.disconnect()

async def main():
    while True:
        phone = input("\nВведи номер телефона (или q для выхода): ")
        if phone.lower() == "q":
            break

        await add_account(phone)

if __name__ == "__main__":
    asyncio.run(main())