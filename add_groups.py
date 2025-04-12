import time
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.contacts import InviteToChannelRequest
import asyncio

API_ID = 'your_api_id'  # Замените на ваш API_ID
API_HASH = 'your_api_hash'  # Замените на ваш API_HASH

# Путь к файлу сессии
SESSION_DIR = 'sessions'

# Функция для чтения номеров телефонов из файла sessions.txt
def read_sessions_from_file():
    if not os.path.exists('sessions.txt'):
        print("❌ Файл sessions.txt не найден")
        return []
    
    with open('sessions.txt', 'r') as f:
        phones = [line.strip() for line in f.readlines()]
    return phones

# Функция для чтения ссылок на группы из файла groups.txt
def read_groups_from_file():
    if not os.path.exists('groups.txt'):
        print("❌ Файл groups.txt не найден")
        return []
    
    with open('groups.txt', 'r') as f:
        groups = [line.strip() for line in f.readlines()]
    return groups

# Функция для вступления в группу
async def join_group(client, group_link):
    try:
        # Преобразуем ссылку в объект чата
        group = await client.get_entity(group_link)
        
        # Вступаем в группу
        await client(InviteToChannelRequest(group, [client.get_me()]))  # Используем InviteToChannelRequest
        print(f"✅ Вступил в группу: {group_link}")
    except FloodWaitError as e:
        # Если ограничение на вступление, ждем указанное время
        print(f"❌ Превышено количество вступлений. Ожидание {e.seconds} секунд.")
        time.sleep(e.seconds)
        return False  # Возвращаем False, чтобы продолжить попытки
    except Exception as e:
        print(f"❌ Ошибка при вступлении в группу {group_link}: {str(e)}")
        return False

    return True

# Основная функция для работы с аккаунтами
async def join_groups():
    phones = read_sessions_from_file()
    groups = read_groups_from_file()

    if not phones or not groups:
        print("❌ Нет сессий или групп для обработки.")
        return

    for phone in phones:
        session_file = os.path.join(SESSION_DIR, f"{phone.replace('+', '').replace(' ', '')}.session")
        
        if not os.path.exists(session_file):
            print(f"❌ Сессия для номера {phone} не найдена.")
            continue

        print(f"🚀 Запуск клиента для номера {phone}...")
        client = TelegramClient(session_file, API_ID, API_HASH)

        await client.start()

        joined_count = 0
        for group_link in groups:
            if joined_count >= 5:
                print("❌ Достигнуто ограничение на количество вступлений, ожидаем 10 минут...")
                time.sleep(600)  # Ждем 10 минут (600 секунд)
                joined_count = 0  # Сбрасываем счетчик

            success = await join_group(client, group_link)
            if success:
                joined_count += 1

        print(f"🚀 Завершено вступление в группы для {phone}.")

if __name__ == '__main__':
    asyncio.run(join_groups())