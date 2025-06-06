import os
from telethon import TelegramClient, events
import asyncio
import math

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, 'w') as f:
        pass

message_map = {}

def remove_invalid_session_from_file(phone):
    try:
        with open(SESSIONS_FILE, "r") as f:
            lines = f.readlines()

        with open(SESSIONS_FILE, "w") as f:
            for line in lines:
                if line.strip() != phone:
                    f.write(line)
        print(f"Номер {phone} удален из sessions.txt")
    except Exception as e:
        print(f"Ошибка при удалении поврежденной сессии: {e}")

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
            os.remove(session_file)
            remove_invalid_session_from_file(phone)
            return None

        me = await client.get_me()
        print(f"✅ Клиент {phone} запущен как: {me.first_name} (@{me.username})")
        return client
    except Exception as e:
        print(f"❌ Ошибка при запуске клиента {phone}: {str(e)}")
        os.remove(session_file)
        remove_invalid_session_from_file(phone)
        return None

async def main():
    with open(SESSIONS_FILE, "r") as f:
        phones = [line.strip() for line in f.readlines() if line.strip()]

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

    # === HANDLER: Новое сообщение ===
    @events.register(events.NewMessage())
    async def handler(event):
        try:
            chat_id = event.chat_id
            sender = await event.get_sender()

            if chat_id == source_chat and sender.id == (await event.client.get_me()).id:
                message = event.message
                print(f"📨 Новое сообщение от владельца, пересылаем...")

                batch_size = 10
                delay_between_batches = 5
                total_batches = math.ceil(len(target_chats) / batch_size)

                for batch_index in range(total_batches):
                    batch = target_chats[batch_index * batch_size : (batch_index + 1) * batch_size]
                    for target in batch:
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
                                sent = await event.client.send_file(
                                    target, message.media, caption=message.text, reply_to=reply_to)
                            else:
                                sent = await event.client.send_message(
                                    target, message.text, reply_to=reply_to)

                            if message.id not in message_map:
                                message_map[message.id] = {}
                            message_map[message.id][target] = sent.id

                            print(f"✅ Отправлено в чат {target}: ID {sent.id}")
                        except Exception as e:
                            print(f"❌ Ошибка при отправке в {target}: {str(e)}")

                    if batch_index < total_batches - 1:
                        print(f"⏳ Ждем {delay_between_batches} секунд...")
                        await asyncio.sleep(delay_between_batches)
            else:
                print("❌ Сообщение не от владельца или не из исходного чата")
        except Exception as e:
            print(f"❌ Ошибка в обработчике NewMessage: {str(e)}")

    # === HANDLER: Редактирование ===
    @events.register(events.MessageEdited())
    async def edit_handler(event):
        try:
            if event.chat_id == source_chat:
                msg_id = event.message.id
                print("✏️ Изменено сообщение в исходном чате")
                if msg_id in message_map:
                    for target in target_chats:
                        try:
                            target_id = message_map[msg_id].get(target)
                            if target_id:
                                msg = await event.client.get_messages(target, ids=target_id)
                                if msg:
                                    await msg.edit(event.message.text)
                                    print(f"✅ Изменено в чате {target}")
                        except Exception as e:
                            print(f"❌ Ошибка редактирования в {target}: {e}")
        except Exception as e:
            print(f"❌ Ошибка в edit_handler: {e}")

    # === HANDLER: Удаление ===
    @events.register(events.MessageDeleted())
    async def delete_handler(event):
        try:
            if event.chat_id == source_chat:
                for msg_id in event.deleted_ids:
                    if msg_id in message_map:
                        for target in target_chats:
                            try:
                                target_id = message_map[msg_id].get(target)
                                if target_id:
                                    await event.client.delete_messages(target, target_id)
                                    print(f"🗑️ Удалено в чате {target}")
                            except Exception as e:
                                print(f"❌ Ошибка удаления в {target}: {e}")
        except Exception as e:
            print(f"❌ Ошибка в delete_handler: {e}")

    # Назначаем обработчики каждому клиенту
    for client in clients:
        client.add_event_handler(handler)
        client.add_event_handler(edit_handler)
        client.add_event_handler(delete_handler)

    print("👂 Слушаем сообщения...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())