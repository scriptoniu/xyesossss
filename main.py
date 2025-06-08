import os
import asyncio
import socks
from collections import deque
from itertools import cycle
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
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

# Глобальные переменные
message_map = {}
message_queue = deque()
is_processing = False

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
    """Подключение клиента"""
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

async def message_sender():
    """Обработчик очереди сообщений"""
    global is_processing
    while message_queue:
        is_processing = True
        target, message, reply_to, client = message_queue.popleft()
        
        try:
            if message.media:
                sent = await client.send_file(
                    target,
                    message.media,
                    caption=message.text or "",
                    reply_to=reply_to
                )
            else:
                sent = await client.send_message(
                    target,
                    message.text,
                    reply_to=reply_to
                )
            
            if message.id not in message_map:
                message_map[message.id] = {}
            message_map[message.id][target] = sent.id
            print(f"✅ [@{client.session.filename}] Отправлено в {target}")
            
        except FloodWaitError as e:
            print(f"⏳ [@{client.session.filename}] FloodWait {e.seconds} сек")
            message_queue.appendleft((target, message, reply_to, client))
            await asyncio.sleep(e.seconds + 1)
            
        except Exception as e:
            print(f"❌ [@{client.session.filename}] Ошибка: {str(e)[:50]}...")
            await asyncio.sleep(3)
            
        finally:
            await asyncio.sleep(0.3)  # Базовая задержка
    
    is_processing = False

async def main():
    # Инициализация
    proxies = load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None
    print(f"🛡 Загружено прокси: {len(proxies)}")

    # Загрузка конфигурации
    with open(SESSIONS_FILE) as f:
        phones = [f"+{line.strip()}" for line in f if line.strip()]
    
    source_chat = int(open("source_chat.txt").read().strip())
    target_chats = [int(line.strip()) for line in open("target_chats.txt") if line.strip()]
    
    print(f"🔔 Исходный чат: {source_chat}")
    print(f"🎯 Целевые чаты: {target_chats}")

    # Подключение клиентов
    clients = []
    for phone in phones:
        proxy = next(proxy_cycle) if proxy_cycle else None
        client = await start_client(phone, proxy)
        if client: 
            clients.append(client)
            await asyncio.sleep(2)  # Задержка между подключениями

    if not clients:
        print("❌ Нет активных клиентов")
        return

    print(f"🚀 Успешно подключено: {len(clients)} клиентов")

    # Обработчик сообщений
    @events.register(events.NewMessage(chats=source_chat))
    async def handler(event):
        if event.sender_id == (await event.client.get_me()).id:
            print(f"\n📨 Новое сообщение (ID: {event.message.id})")
            
            for target in target_chats:
                reply_to = None
                if event.message.reply_to_msg_id:
                    replied = await event.message.get_reply_message()
                    if replied and replied.id in message_map:
                        reply_to = message_map[replied.id].get(target)
                
                message_queue.append((target, event.message, reply_to, event.client))
            
            if not is_processing:
                asyncio.create_task(message_sender())

    # Регистрация обработчиков
    for client in clients:
        client.add_event_handler(handler)

    print("\n👂 Ожидаем сообщения... (Ctrl+C для выхода)")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())