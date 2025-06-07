import os
import asyncio
import socks
from telethon import TelegramClient, events

API_ID = 25293202
API_HASH = '68a935aff803647b47acf3fb28a3d765'

SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'
PROXY_FILE = 'proxies.txt'

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

if not os.path.exists(SESSIONS_FILE):
    open(SESSIONS_FILE, 'w').close()

if not os.path.exists(PROXY_FILE):
    open(PROXY_FILE, 'w').close()

message_map = {}

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

def load_proxies():
    proxies = []
    with open(PROXY_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split(':')
            if len(parts) == 2:
                ip, port = parts
                proxy = (socks.SOCKS5, ip, int(port))
            elif len(parts) == 4:
                ip, port, user, pwd = parts
                proxy = (socks.SOCKS5, ip, int(port), True, user, pwd)
            else:
                continue
            proxies.append(proxy)
    return proxies

async def start_client(phone, proxy=None):
    session_file = os.path.join(SESSION_DIR, f"{phone.replace('+', '')}.session")
    if not os.path.exists(session_file):
        print(f"❌ Сессия не найдена: {phone}")
        return None

    try:
        client = TelegramClient(session_file, API_ID, API_HASH, proxy=proxy)
        await client.connect()
        print(f"🔄 Подключение выполнено для {phone}")

        if not await client.is_user_authorized():
            print(f"❌ Сессия недействительна: {phone}")
            if os.path.exists(session_file):
                os.remove(session_file)
            remove_invalid_session_from_file(phone)
            return None

        me = await client.get_me()
        print(f"✅ Клиент {phone} запущен как {me.first_name} (@{me.username})")
        return client

    except Exception as e:
        print(f"⚠️ Ошибка при запуске клиента {phone}: {e}")
        if os.path.exists(session_file):
            os.remove(session_file)
        remove_invalid_session_from_file(phone)
        return None

async def main():
    with open(SESSIONS_FILE, "r") as f:
        phones = [line.strip() for line in f if line.strip()]
    print(f"📋 Загружены телефоны: {phones}")

    with open(PROXY_FILE, "r") as f:
        proxy_list = [line.strip() for line in f if line.strip()]
    print(f"🛡 Загружено прокси: {len(proxy_list)} шт.")

    proxies = load_proxies()

    with open("source_chat.txt", "r") as f:
        source_chat = int(f.read().strip())

    with open("target_chats.txt", "r") as f:
        target_chats = [int(line.strip()) for line in f if line.strip()]

    clients = []
    for idx, phone in enumerate(phones):
        proxy = proxies[idx // 10] if idx // 10 < len(proxies) else None
        if proxy:
            print(f"🔑 Запуск клиента для +{phone} с прокси: {proxy}")
        else:
            print(f"🔑 Запуск клиента для +{phone} без прокси")
        client = await start_client(f"+{phone}", proxy)
        if client:
            clients.append(client)

    if not clients:
        print("❌ Нет активных клиентов.")
        return

    print(f"✅ Активных клиентов: {len(clients)}")

    @events.register(events.NewMessage())
    async def handler(event):
        try:
            chat_id = event.chat_id
            sender = await event.get_sender()
            me = await event.client.get_me()

            if chat_id == source_chat and sender.id == me.id:
                message = event.message
                print(f"📨 Новое сообщение, пересылаем...")

                for target in target_chats:
                    try:
                        reply_to = None
                        if message.reply_to:
                            replied = await message.get_reply_message()
                            if replied:
                                async for msg in event.client.iter_messages(target, search=replied.text):
                                    if msg.text == replied.text:
                                        reply_to = msg.id
                                        break

                        if message.media:
                            sent_message = await event.client.send_file(
                                target, message.media,
                                caption=message.text or "",
                                reply_to=reply_to
                            )
                        else:
                            sent_message = await event.client.send_message(
                                target, message.text,
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

    @events.register(events.MessageEdited())
    async def edit_handler(event):
        try:
            chat_id = event.chat_id
            message_id = event.message.id
            sender = await event.get_sender()
            me = await event.client.get_me()

            if chat_id == source_chat and sender.id == me.id:
                if message_id in message_map:
                    for target in target_chats:
                        try:
                            target_message_id = message_map[message_id].get(target)
                            if target_message_id:
                                await event.client.edit_message(target, target_message_id, event.message.text)
                                print(f"✏️ Изменено в чате {target}")
                        except Exception as e:
                            print(f"❌ Ошибка редактирования в {target}: {e}")
        except Exception as e:
            print(f"⚠️ Ошибка в MessageEdited: {e}")

    @events.register(events.MessageDeleted())
    async def delete_handler(event):
        try:
            chat_id = event.chat_id
            deleted_ids = event.deleted_ids

            if chat_id == source_chat:
                for msg_id in deleted_ids:
                    if msg_id in message_map:
                        for target in target_chats:
                            try:
                                target_msg_id = message_map[msg_id].get(target)
                                if target_msg_id:
                                    await event.client.delete_messages(target, target_msg_id)
                                    print(f"🗑 Удалено в чате {target}")
                            except Exception as e:
                                print(f"❌ Ошибка удаления в {target}: {e}")
        except Exception as e:
            print(f"⚠️ Ошибка в MessageDeleted: {e}")

    for client in clients:
        client.add_event_handler(handler)
        client.add_event_handler(edit_handler)
        client.add_event_handler(delete_handler)

    print("👂 Ожидаем события...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())