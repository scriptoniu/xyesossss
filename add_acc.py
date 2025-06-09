import os
import asyncio
import socks
from itertools import cycle
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = 25293202
API_HASH = '68a935aff803647b47acf3fb28a3d765'

SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'
PROXY_FILE = 'proxies.txt'

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w'):
        pass

def add_account_to_file(phone):
    with open(SESSIONS_FILE, 'r') as f:
        lines = f.readlines()
    lines = [line.strip() for line in lines if line.strip() != phone]
    lines.append(phone)
    with open(SESSIONS_FILE, 'w') as f:
        for line in lines:
            f.write(line + "\n")

def load_proxies():
    proxies = []
    if not os.path.exists(PROXY_FILE):
        return proxies

    with open(PROXY_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(':')
            try:
                if len(parts) == 2:
                    proxy = (socks.SOCKS5, parts[0], int(parts[1]))
                elif len(parts) == 4:
                    proxy = (socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3])
                else:
                    continue
                proxies.append(proxy)
            except Exception:
                continue
    return proxies

async def add_account(phone, proxy=None):
    session_name = os.path.join(SESSION_DIR, phone.replace("+", "").replace(" ", ""))
    client = TelegramClient(session_name, API_ID, API_HASH, proxy=proxy)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input(f"Введите код для {phone}: ")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input(f"Введите 2FA пароль для {phone}: ")
                await client.sign_in(password=password)

        if await client.is_user_authorized():
            print(f"✅ Сессия сохранена: {session_name}.session")
            add_account_to_file(phone)
        else:
            print("❌ Ошибка авторизации")
    except Exception as e:
        print(f"⚠️ Ошибка при подключении {phone}: {e}")
    finally:
        await client.disconnect()

async def main():
    proxies = load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None

    while True:
        phone = input("\nВведите номер телефона (или q для выхода): ")
        if phone.lower() == "q":
            break

        proxy = next(proxy_cycle) if proxy_cycle else None
        print(f"🔌 Используется прокси: {proxy[1] if proxy else 'нет'}")
        await add_account(phone, proxy)

if __name__ == "__main__":
    asyncio.run(main())