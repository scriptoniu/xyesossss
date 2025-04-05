import os
from telethon import TelegramClient, events
import asyncio

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

# Словарь для хранения ID сообщений: {source_message_id: {target_chat_id: target_message_id}}
message_map = {}

# Папка для хранения файлов .session
SESSION_DIR = 'sessions'

# Убедитесь, что папка для сессий существует
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

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
            return None

        me = await client.get_me()
        print(f"✅ Клиент {phone} запущен как: {me.first_name} (@{me.username})")
        return client
    except Exception as e:
        print(f"❌ Ошибка при запуске клиента {phone}: {str(e)}")
        return None

async def main():
    # Читаем все номера из файла sessions.txt
    with open("sessions.txt", "r") as f:
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

    @events.register(events.MessageEdited())
    async def edit_handler(event):
        try:
            chat_id = event.chat_id
            message_id = event.message.id
            sender = await event.get_sender()

            if chat_id == source_chat and sender.id == (await event.client.get_me()).id:
                print(f"✏️ Изменено сообщение в исходном чате")

                if message_id in message_map:
                    for target in target_chats:
                        try:
                            target_message_id = message_map[message_id].get(target)
                            if target_message_id:
                                target_message = await event.client.get_messages(target, ids=target_message_id)
                                if target_message:
                                    await target_message.edit(event.message.text)
                                    print(f"✅ Изменено в чате {target}")
                        except Exception as e:
                            print(f"❌ Ошибка при редактировании в {target}: {str(e)}")
        except Exception as e:
            print(f"❌ Ошибка в обработчике MessageEdited: {str(e)}")

    @events.register(events.MessageDeleted())
    async def delete_handler(event):
        try:
            chat_id = event.chat_id
            deleted_message_ids = event.deleted_ids

            if chat_id == source_chat:
                print(f"❌ Удалено сообщение в исходном чате")

                for message_id in deleted_message_ids:
                    if message_id in message_map:
                        for target in target_chats:
                            try:
                                target_message_id = message_map[message_id].get(target)
                                if target_message_id:
                                    await event.client.delete_messages(target, target_message_id)
                                    print(f"✅ Удалено в чате {target}")
                            except Exception as e:
                                print(f"❌ Ошибка при удалении в {target}: {str(e)}")
        except Exception as e:
            print(f"❌ Ошибка в обработчике MessageDeleted: {str(e)}")

    # Назначаем обработчики каждому клиенту
    for client in clients:
        client.add_event_handler(handler)
        client.add_event_handler(edit_handler)
        client.add_event_handler(delete_handler)

    print("👂 Боты слушают сообщения...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())