import os
from telethon import TelegramClient, events
import asyncio

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'  # Теперь правильно указываем sessions.txt

# Убедитесь, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# Проверяем, существует ли файл sessions.txt, если нет - создаем его
if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w') as f:
        pass  # Пустой файл будет создан

# Функция для удаления битой сессии
def remove_invalid_session_from_file(phone):
    """Удаляет номер телефона из файла sessions.txt, если сессия битая."""
    try:
        with open(SESSIONS_FILE, "r") as f:
            lines = f.readlines()

        # Удаляем строку с номером телефона
        with open(SESSIONS_FILE, "w") as f:
            for line in lines:
                if line.strip() != phone:
                    f.write(line)
    except Exception as e:
        print(f"❌ Ошибка при удалении сессии из файла {SESSIONS_FILE}: {str(e)}")

async def start_client(phone):
    print(f"🚀 Запуск клиента {phone}...")

    session_file = os.path.join(SESSION_DIR, f"{phone.replace('+', '')}.session")
    if not os.path.exists(session_file):
        print(f"❌ Сессия {phone} не найдена")
        return None

    try:
        client = TelegramClient(session_file, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"❌ Сессия {phone} недействительна")
            # Удаляем сессию и из файла, и из папки
            os.remove(session_file)
            remove_invalid_session_from_file(phone)
            return None

        me = await client.get_me()
        print(f"✅ Клиент {phone} запущен как: {me.first_name} (@{me.username})")
        return client
    except Exception as e:
        print(f"❌ Ошибка при запуске клиента {phone}: {str(e)}")
        return None

async def main():
    # Читаем все номера из файла sessions.txt
    with open(SESSIONS_FILE, "r") as f:
        phones = [line.strip() for line in f.readlines() if line.strip()]

    # Читаем исходный и целевые чаты
    with open("source_chat.txt", "r") as f:
        source_chat = int(f.read().strip())

    with open("target_chats.txt", "r") as f:
        target_chats = [int(line.strip()) for line in f.readlines()]

    clients = []
    for phone in phones:
        client = await start_client(f"+{phone}")
        if client:
            clients.append(client)

    if not clients:
        print("❌ Нет доступных клиентов")
        return

    print(f"✅ Запущено клиентов: {len(clients)}")

    @events.register(events.NewMessage())
    async def handler(event):
        try:
            chat_id = event.chat_id
            sender = await event.get_sender()

            if chat_id == source_chat and sender.id == (await event.client.get_me()).id:
                message = event.message
                print(f"📨 Новое сообщение от владельца, пересылаем...")

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
                            sent_message = await event.client.send_file(target, message.media, caption=message.text, reply_to=reply_to)
                        else:
                            sent_message = await event.client.send_message(target, message.text, reply_to=reply_to)

                        # Сохраняем в message_map
                        if message.id not in message_map:
                            message_map[message.id] = {}
                        message_map[message.id][target] = sent_message.id

                        print(f"✅ Отправлено в чат {target}: ID {sent_message.id}")
                    except Exception as e:
                        print(f"❌ Ошибка при отправке в {target}: {str(e)}")
            else:
                print(f"❌ Сообщение от другого пользователя или чата")
        except Exception as e:
            print(f"❌ Ошибка в обработчике NewMessage: {str(e)}")

    # Назначаем обработчики каждому клиенту
    for client in clients:
        client.add_event_handler(handler)

    print("👂 Боты слушают сообщения...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())