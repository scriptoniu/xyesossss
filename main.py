import os
import asyncio
import socks
from itertools import cycle
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Загрузка конфигурации
load_dotenv()
API_ID = int(os.getenv('API_ID', 25293202))
API_HASH = os.getenv('API_HASH', '68a935aff803647b47acf3fb28a3d765')
PROXY_FILE = 'proxies.txt'

# Настройка директорий
SESSION_DIR = 'sessions'
os.makedirs(SESSION_DIR, exist_ok=True)
SESSIONS_FILE = 'sessions.txt'
if not os.path.exists(SESSIONS_FILE):
    open(SESSIONS_FILE, 'w').close()

message_map = {}

def load_proxies():
    """Загрузка прокси из файла"""
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split(':')
                try:
                    if len(parts) == 2:
                        proxy = (socks.SOCKS5, parts[0], int(parts[1]))
                    elif len(parts) == 4:
                        proxy = (socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3])
                    else: continue
                    proxies.append(proxy)
                except (ValueError, IndexError): continue
    return proxies

async def start_client(phone, proxy=None):
    """Подключение клиента с автоматическим переключением прокси"""
    session_file = os.path.join(SESSION_DIR, f"{phone.replace('+', '')}.session")
    if not os.path.exists(session_file):
        print(f"❌ Сессия не найдена: {phone}")
        return None

    try:
        client = TelegramClient(session_file, API_ID, API_HASH, proxy=proxy)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ Сессия недействительна: {phone}")
            os.remove(session_file)
            return None
        me = await client.get_me()
        print(f"✅ {phone} запущен как @{me.username}")
        return client
    except Exception as e:
        print(f"⚠️ Ошибка подключения {phone}: {str(e)[:50]}...")
        if os.path.exists(session_file):
            os.remove(session_file)
        return None

async def main():
    # Инициализация
    proxies = load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None
    print(f"🛡 Загружено прокси: {len(proxies)}")

    # Загрузка конфигурации
    with open(SESSIONS_FILE) as f:
        phones = [f"+{line.strip()}" for line in f if line.strip()]
    
    source_chat = int(open("source_chat.txt").read().strip())
    
    # Чтение чатов по порядку и удаление дубликатов
    with open("target_chats.txt") as f:
        target_chats = sorted(list({int(line.strip()) for line in f if line.strip()}))
    
    print(f"🔔 Исходный чат: {source_chat}")
    print(f"🎯 Целевые чаты (по порядку): {target_chats}")

    # Подключение клиентов
    clients = []
    for phone in phones:
        proxy = next(proxy_cycle) if proxy_cycle else None
        client = await start_client(phone, proxy)
        if client: clients.append(client)
        await asyncio.sleep(2)  # Оптимизированная задержка между подключениями

    if not clients:
        print("❌ Нет активных клиентов")
        return

    print(f"🚀 Успешно подключено: {len(clients)} клиентов")

    # Обработчики сообщений
    @events.register(events.NewMessage(chats=source_chat))
    async def handler(event):
        if event.sender_id == (await event.client.get_me()).id:
            print(f"\n📨 Новое сообщение (ID: {event.message.id})")
            
            for target in target_chats:  # Отправка по порядку
                try:
                    # Упрощенная отправка с задержкой 0.3 сек
                    if event.message.media:
                        sent = await event.client.send_file(
                            target,
                            event.message.media,
                            caption=event.message.text
                        )
                    else:
                        sent = await event.client.send_message(
                            target,
                            event.message.text
                        )
                    print(f"✅ Отправлено в {target}: {sent.id}")
                    await asyncio.sleep(0.3)  # Задержка между чатами 0.3 сек
                except Exception as e:
                    print(f"❌ Ошибка в {target}: {str(e)[:50]}...")

    # Регистрация обработчиков
    for client in clients:
        client.add_event_handler(handler)

    print("\n👂 Ожидаем сообщения... (Ctrl+C для выхода)")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())