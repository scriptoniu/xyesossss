import os
import asyncio
import socks
from itertools import cycle
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# Конфигурация
API_ID = 25293202
API_HASH = '68a935aff803647b47acf3fb28a3d765'
SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'
PROXY_FILE = 'proxies.txt'

# Создаем необходимые файлы/директории
os.makedirs(SESSION_DIR, exist_ok=True)
for file in [SESSIONS_FILE, PROXY_FILE]:
    if not os.path.exists(file):
        open(file, 'w').close()

message_map = {}

def load_proxies():
    """Загружает прокси из файла в формате ip:port[:login:password]"""
    proxies = []
    with open(PROXY_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) == 2:
                proxy = (socks.SOCKS5, parts[0], int(parts[1]))
            elif len(parts) == 4:
                proxy = (socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3])
            else:
                continue
            proxies.append(proxy)
    return proxies

def remove_invalid_session(phone):
    """Удаляет невалидный номер из sessions.txt"""
    try:
        with open(SESSIONS_FILE, "r+") as f:
            lines = [line.strip() for line in f if line.strip() != phone]
            f.seek(0)
            f.write('\n'.join(lines))
            f.truncate()
        print(f"📤 Удалена сессия: {phone}")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении сессии: {e}")

async def start_client(phone, proxy):
    """Запускает клиент с указанным прокси"""
    session_file = os.path.join(SESSION_DIR, phone.replace('+', '') + '.session')
    
    try:
        client = TelegramClient(session_file, API_ID, API_HASH, proxy=proxy)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"❌ Сессия недействительна: {phone}")
            os.remove(session_file)
            remove_invalid_session(phone)
            return None

        me = await client.get_me()
        print(f"✅ {phone} запущен как {me.first_name} (@{me.username})")
        return client

    except Exception as e:
        print(f"⚠️ Ошибка при запуске {phone}: {e}")
        if os.path.exists(session_file):
            os.remove(session_file)
        remove_invalid_session(phone)
        return None

async def main():
    # Загрузка конфигурации
    with open(SESSIONS_FILE, "r") as f:
        phones = ['+' + line.strip() for line in f if line.strip()]
    
    with open("source_chat.txt") as f:
        source_chat = int(f.read().strip())
    
    with open("target_chats.txt") as f:
        target_chats = [int(line.strip()) for line in f if line.strip()]

    # Настройка прокси
    proxies = load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None
    print(f"🛡 Загружено прокси: {len(proxies)}")

    # Семафор для ограничения одновременных запросов
    semaphore = asyncio.Semaphore(5)

    # Запуск клиентов
    clients = []
    for i, phone in enumerate(phones):
        proxy = proxy_cycle.__next__() if proxy_cycle else None
        print(f"🔁 Подключаем {phone} через прокси: {proxy[:2] if proxy else 'нет'}")
        
        client = await start_client(phone, proxy)
        if client:
            clients.append(client)
        
        # Задержка между подключениями
        if i < len(phones) - 1:
            await asyncio.sleep(3)

    if not clients:
        print("❌ Нет активных клиентов")
        return

    print(f"🚀 Успешно запущено клиентов: {len(clients)}")

    async def safe_send_message(client, target, message, reply_to=None):
        """Безопасная отправка с ограничением частоты"""
        async with semaphore:
            try:
                if message.media:
                    sent = await client.send_file(target, message.media, 
                                                caption=message.text,
                                                reply_to=reply_to)
                else:
                    sent = await client.send_message(target, message.text,
                                                   reply_to=reply_to)
                
                # Сохраняем ID сообщения для редактирования
                if message.id not in message_map:
                    message_map[message.id] = {}
                message_map[message.id][target] = sent.id
                
                print(f"📨 {client.session.filename}: Отправлено в {target}")
                await asyncio.sleep(1)  # Задержка между сообщениями
                return sent
            except Exception as e:
                print(f"⚠️ Ошибка отправки: {e}")
                await asyncio.sleep(5)  # Большая задержка при ошибке
                return None

    @events.register(events.NewMessage(chats=source_chat))
    async def message_handler(event):
        if event.sender_id == (await event.client.get_me()).id:
            print(f"🔔 Новое сообщение для пересылки (ID: {event.message.id})")
            
            for target in target_chats:
                reply_to = None
                if event.message.reply_to_msg_id:
                    original_reply = await event.message.get_reply_message()
                    if original_reply and original_reply.id in message_map:
                        reply_to = message_map[original_reply.id].get(target)
                
                await safe_send_message(event.client, target, event.message, reply_to)

    # Регистрируем обработчики
    for client in clients:
        client.add_event_handler(message_handler)

    print("👂 Ожидаем сообщения...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())