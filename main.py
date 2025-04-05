from telethon import TelegramClient, events
import asyncio
import os

API_ID = 25293202  # Заменить на свой API ID
API_HASH = '68a935aff803647b47acf3fb28a3d765'  # Заменить на свой API HASH

# Словарь для хранения ID сообщений, чтобы отслеживать и синхронизировать их в целевых чатах
message_map = {}

async def start_client(phone):
    print(f"🚀 Запуск клиента {phone}...")

    session_file = f"{phone.replace('+', '')}.session"
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

    # Чтение исходного чата и целевых чатов из файлов
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

            print(f"📨 Получено сообщение в чате {chat_id}")

            # Используем общие source_chat и target_chats
            if chat_id == source_chat and sender.id == (await event.client.get_me()).id:
                print(f"✅ Сообщение от владельца аккаунта")
                message = event.message
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

                        # Отправляем медиа, если оно есть
                        if message.media:
                            sent_message = await event.client.send_file(target, message.media, caption=message.text, reply_to=reply_to)
                        else:
                            sent_message = await event.client.send_message(target, message.text, reply_to=reply_to)

                        # Сохраняем ID отправленного сообщения в целевом чате
                        message_map[message.id] = { "source_chat_id": message.id, "target_chat_id": sent_message.id }
                        print(f"✅ Сообщение отправлено в {target} с ID: {sent_message.id}")
                    except Exception as e:
                        print(f"❌ Ошибка при отправке в {target}: {str(e)}")
            else:
                print(f"❌ Сообщение от неразрешенного пользователя или из другого чата")
        except Exception as e:
            print(f"❌ Ошибка в обработчике: {str(e)}")

    # Обработчик для редактирования сообщений
    @events.register(events.MessageEdited())
    async def edit_handler(event):
        try:
            chat_id = event.chat_id
            message_id = event.message.id
            sender = await event.get_sender()

            # Проверяем, что изменение произошло в исходном чате и от владельца
            if chat_id == source_chat and sender.id == (await event.client.get_me()).id:
                print(f"✅ Изменено сообщение в исходном чате")

                # Если сообщение изменено, мы ищем его в целевых чатах по сохраненному ID
                if message_id in message_map:
                    target_message_id = message_map[message_id]["target_chat_id"]
                    for target in target_chats:
                        try:
                            target_client = event.client
                            # Используем `get_messages` для получения сообщения по ID
                            target_message = await target_client.get_messages(target, ids=target_message_id)
                            if target_message:  # Проверяем, что сообщение найдено
                                # Изменяем текст сообщения в целевом чате
                                await target_message.edit(event.message.text)
                                if event.message.media:
                                    await target_message.edit(file=event.message.media)
                                print(f"✅ Сообщение изменено в целевом чате {target}")
                        except Exception as e:
                            print(f"❌ Ошибка при редактировании в {target}: {str(e)}")
        except Exception as e:
            print(f"❌ Ошибка при редактировании сообщения: {str(e)}")

    # Обработчик для удаления сообщений
    @events.register(events.MessageDeleted())
    async def delete_handler(event):
        try:
            chat_id = event.chat_id
            deleted_message_ids = event.deleted_ids

            # Если удаление происходит в исходном чате и это сообщение владельца
            if chat_id == source_chat:
                print(f"✅ Удалено сообщение в исходном чате")

                # Теперь удаляем сообщение во всех целевых чатах
                for deleted_message_id in deleted_message_ids:
                    if deleted_message_id in message_map:
                        target_message_id = message_map[deleted_message_id]["target_chat_id"]
                        for target in target_chats:
                            try:
                                target_client = event.client
                                # Пытаемся найти и удалить удаленное сообщение в целевом чате
                                target_message = await target_client.get_messages(target, ids=target_message_id)
                                if target_message:
                                    await target_message.delete()
                                    print(f"✅ Сообщение удалено в целевом чате {target}")
                            except Exception as e:
                                print(f"❌ Ошибка при удалении в {target}: {str(e)}")
        except Exception as e:
            print(f"❌ Ошибка при удалении сообщения: {str(e)}")

    # Добавляем обработчики для всех клиентов
    for client in clients:
        client.add_event_handler(handler)
        client.add_event_handler(edit_handler)
        client.add_event_handler(delete_handler)

    print("👂 Боты начали прослушивание...")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == '__main__':
    asyncio.run(main())
