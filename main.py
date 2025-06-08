import os
import asyncio
import socks
from itertools import cycle
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Загрузка конфигурации из .env файла
load_dotenv()
API_ID = int(os.getenv('API_ID', 25293202))
API_HASH = os.getenv('API_HASH', '68a935aff803647b47acf3fb28a3d765')
PROXY_FILE = 'proxies.txt'  # Файл с прокси

SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w'):
        pass

message_map = {}

def load_proxies():
    """Загружает прокси из файла"""
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
            except (ValueError, IndexError):
                continue
    return proxies

def remove_invalid_session_from_file(phone):
    try:
        with open(SESSIONS_FILE, "r") as f:
            lines = f.readlines()
        with open(SESSIONS_FILE, "w") as f:
            for line in lines:
                if line.strip() != phone:
                    f.write(line)
        print(f"📤 Удалена поврежденная сессия: {phone}")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении сессии: {e}")

async def start_client(phone, proxy=None):
    """Запускает клиент с возможностью использования прокси"""
    session_file = os.path.join(SESSION_DIR, f"{phone.replace('+', '')}.session")
    if not os.path.exists(session_file):
        print(f"❌ Сессия не найдена: {phone}")
        return None

    # Сначала пробуем подключиться через прокси (если он есть)
    if proxy:
        try:
            print(f"🔄 Пробуем подключиться через прокси: {proxy[1]}")
            client = TelegramClient(session_file, API_ID, API_HASH, proxy=proxy)
            await client.connect()

            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"✅ Клиент {phone} запущен через ПРОКСИ как {me.first_name} (@{me.username})")
                return client
            else:
                print(f"❌ Не удалось авторизоваться через прокси: {phone}")
                await client.disconnect()
        except Exception as e:
            print(f"⚠️ Ошибка подключения через прокси {phone}: {e}")
    
    # Если прокси не указан или подключение через прокси не удалось
    try:
        print(f"🔄 Пробуем прямое подключение: {phone}")
        client = TelegramClient(session_file, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"❌ Сессия недействительна: {phone}")
            os.remove(session_file)
            remove_invalid_session_from_file(phone)
            return None

        me = await client.get_me()
        print(f"✅ Клиент {phone} запущен БЕЗ ПРОКСИ как {me.first_name} (@{me.username})")
        return client

    except Exception as e:
        print(f"⚠️ Ошибка при запуске клиента {phone}: {e}")
        if os.path.exists(session_file):
            os.remove(session_file)
        remove_invalid_session_from_file(phone)
        return None

async def main():
    # Загрузка прокси
    proxies = load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None
    print(f"🛡 Загружено прокси: {len(proxies)}")

    with open(SESSIONS_FILE, "r") as f:
        phones = [line.strip() for line in f if line.strip()]
    
    with open("source_chat.txt", "r") as f:
        source_chat = int(f.read().strip())
    
    with open("target_chats.txt", "r") as f:
        target_chats = [int(line.strip()) for line in f if line.strip()]

    print(f"🔔 Исходный чат: {source_chat}")
    print(f"🎯 Целевые чаты: {target_chats}")

    clients = []
    for i, phone in enumerate(phones):
        proxy = next(proxy_cycle) if proxy_cycle else None
        print(f"\n🔁 Подключаем +{phone} через прокси: {proxy[1] if proxy else 'нет'}")
        
        client = await start_client(f"+{phone}", proxy)
        if client:
            clients.append(client)
        await asyncio.sleep(3)  # Задержка между подключениями

    if not clients:
        print("❌ Нет активных клиентов.")
        return

    print(f"✅ Активных клиентов: {len(clients)}")

    # Обработчик для логирования ВСЕХ входящих сообщений (для отладки)
    @events.register(events.NewMessage)
    async def debug_handler(event):
        try:
            me = await event.client.get_me()
            sender = await event.get_sender()
            print(f"\n📩 DEBUG: Получено сообщение в чате {event.chat_id}")
            print(f"👤 Отправитель: {sender.id} (Я: {me.id})")
            print(f"💬 Текст: {event.message.text}")
            print(f"🔔 Сообщение от меня: {sender.id == me.id}")
            print(f"🔔 В целевом чате: {event.chat_id == source_chat}")
        except Exception as e:
            print(f"⚠️ Ошибка в debug_handler: {e}")

    # Основной обработчик сообщений
    @events.register(events.NewMessage)
    async def handler(event):
        try:
            chat_id = event.chat_id
            me = await event.client.get_me()
            sender = await event.get_sender()

            # Проверяем, что сообщение в нужном чате и от нашего пользователя
            if chat_id == source_chat and sender.id == me.id:
                message = event.message
                print(f"\n📨 Новое сообщение для пересылки (ID: {message.id})")

                for target in target_chats:
                    try:
                        reply_to = None
                        if message.reply_to_msg_id:
                            print(f"🔍 Поиск сообщения для ответа...")
                            original_reply = await message.get_reply_message()
                            if original_reply:
                                # Упрощенный поиск (для тестирования)
                                reply_to = original_reply.id
                                print(f"↩️ Найдено сообщение для ответа: {reply_to}")

                        print(f"🚀 Отправка в чат {target}...")
                        if message.media:
                            sent_message = await event.client.send_file(
                                target, 
                                message.media,
                                caption=message.text or "",
                                reply_to=reply_to
                            )
                        else:
                            sent_message = await event.client.send_message(
                                target, 
                                message.text,
                                reply_to=reply_to
                            )

                        if message.id not in message_map:
                            message_map[message.id] = {}
                        message_map[message.id][target] = sent_message.id

                        print(f"✅ Отправлено в чат {target}: ID {sent_message.id}")
                    except Exception as e:
                        print(f"❌ Ошибка при отправке в {target}: {e}")
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"⚠️ Ошибка в NewMessage: {e}")

    for client in clients:
        # Регистрируем обработчики для каждого клиента
        client.add_event_handler(debug_handler)  # Для отладки
        client.add_event_handler(handler)
        
        # Включаем режим отладки для клиента
        client.parse_mode = 'html'  # Улучшенное логирование

    print("\n👂 Ожидаем события... (Для выхода: Ctrl+C)")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())