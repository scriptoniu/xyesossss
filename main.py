import os
import asyncio
import socks
from itertools import cycle
from telethon import TelegramClient, events
import logging
from datetime import datetime
from dotenv import load_dotenv

# Загрузка конфигурации
load_dotenv()
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
LOG_BOT_TOKEN = os.getenv('LOG_BOT_TOKEN')
LOG_CHAT_ID = int(os.getenv('LOG_CHAT_ID'))

# Константы
SESSION_DIR = 'sessions'
SESSIONS_FILE = 'sessions.txt'
PROXY_FILE = 'proxies.txt'

# Настройка логирования в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class ErrorLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = None
        return cls._instance

    async def initialize(self):
        try:
            self.client = TelegramClient('error_logger', API_ID, API_HASH)
            await self.client.start(bot_token=LOG_BOT_TOKEN)
            logger.info("Логгер ошибок инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации логгера: {e}")

    async def log_error(self, error_message):
        try:
            if self.client and self.client.is_connected():
                await self.client.send_message(LOG_CHAT_ID, error_message)
        except Exception as e:
            logger.error(f"Не удалось отправить ошибку в Telegram: {e}")

async def setup_error_logger():
    logger_instance = ErrorLogger()
    await logger_instance.initialize()
    return logger_instance

async def load_proxies():
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
            except (ValueError, IndexError) as e:
                error_msg = f"Ошибка парсинга прокси {line}: {e}"
                logger.error(error_msg)
    return proxies

async def start_client(phone, proxy, error_logger):
    """Запускает клиент с обработкой ошибок"""
    session_file = os.path.join(SESSION_DIR, phone.replace('+', '') + '.session')
    
    try:
        client = TelegramClient(session_file, API_ID, API_HASH, proxy=proxy)
        await client.connect()

        if not await client.is_user_authorized():
            error_msg = f"Сессия недействительна: {phone}"
            logger.error(error_msg)
            await error_logger.log_error(f"❌ {error_msg}")
            return None

        me = await client.get_me()
        logger.info(f"[{phone} запущен как @{me.username}]")
        return client

    except Exception as e:
        error_msg = f"Ошибка подключения {phone}: {type(e).__name__} - {str(e)}"
        logger.error(error_msg)
        await error_logger.log_error(f"⚠️ {error_msg}")
        return None

async def safe_send_message(client, target, message, reply_to, error_logger):
    """Безопасная отправка сообщения"""
    try:
        if message.media:
            sent = await client.send_file(
                target,
                message.media,
                caption=message.text,
                reply_to=reply_to
            )
        else:
            sent = await client.send_message(
                target,
                message.text,
                reply_to=reply_to
            )
        
        logger.info(f"Отправлено в чат {target}: ID {sent.id}")
        await asyncio.sleep(1)  # Задержка 1 секунда
        return sent
    except Exception as e:
        error_msg = f"Ошибка отправки в {target}: {type(e).__name__} - {str(e)}"
        logger.error(error_msg)
        await error_logger.log_error(f"⚠️ {error_msg}")
        await asyncio.sleep(3)
        return None

async def main():
    # Инициализация логгера ошибок
    error_logger = await setup_error_logger()
    await error_logger.log_error("🟢 Бот запущен")

    # Проверка файлов
    os.makedirs(SESSION_DIR, exist_ok=True)
    for file in [SESSIONS_FILE, 'source_chat.txt', 'target_chats.txt']:
        if not os.path.exists(file):
            open(file, 'w').close()

    # Загрузка данных
    try:
        with open(SESSIONS_FILE) as f:
            phones = ['+' + line.strip() for line in f if line.strip()]
        
        with open("source_chat.txt") as f:
            source_chat = int(f.read().strip())
        
        with open("target_chats.txt") as f:
            target_chats = [int(line.strip()) for line in f if line.strip()]
    except Exception as e:
        error_msg = f"Ошибка загрузки конфигурации: {e}"
        logger.error(error_msg)
        await error_logger.log_error(f"❌ {error_msg}")
        return

    # Загрузка прокси
    proxies = await load_proxies()
    proxy_cycle = cycle(proxies) if proxies else None
    logger.info(f"[Загружено прокси: {len(proxies)}]")

    # Запуск клиентов
    clients = []
    for i, phone in enumerate(phones):
        proxy = next(proxy_cycle) if proxy_cycle else None
        logger.info(f"Подключаем {phone} через прокси: {proxy[:2] if proxy else 'нет'}")
        
        client = await start_client(phone, proxy, error_logger)
        if client:
            clients.append(client)
            await asyncio.sleep(3)  # Задержка между подключениями

    if not clients:
        error_msg = "Нет активных клиентов"
        logger.error(error_msg)
        await error_logger.log_error(f"❌ {error_msg}")
        return

    logger.info(f"[Успешно запущено клиентов: {len(clients)}]")

    message_map = {}

    @events.register(events.NewMessage(chats=source_chat))
    async def message_handler(event):
        try:
            me = await event.client.get_me()
            if event.sender_id == me.id:
                logger.info(f"Новое сообщение для пересылки (ID: {event.message.id})")
                
                for target in target_chats:
                    reply_to = None
                    if event.message.reply_to_msg_id:
                        original_reply = await event.message.get_reply_message()
                        if original_reply and original_reply.id in message_map:
                            reply_to = message_map[original_reply.id].get(target)
                    
                    sent_message = await safe_send_message(
                        event.client,
                        target,
                        event.message,
                        reply_to,
                        error_logger
                    )
                    
                    if sent_message:
                        if event.message.id not in message_map:
                            message_map[event.message.id] = {}
                        message_map[event.message.id][target] = sent_message.id
        except Exception as e:
            error_msg = f"Ошибка в обработчике сообщений: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            await error_logger.log_error(f"⚠️ {error_msg}")

    # Регистрация обработчиков
    for client in clients:
        client.add_event_handler(message_handler)

    logger.info("Ожидаем сообщения...")

    try:
        await asyncio.gather(*[client.run_until_disconnected() for client in clients])
    except Exception as e:
        error_msg = f"Критическая ошибка: {type(e).__name__} - {str(e)}"
        logger.critical(error_msg)
        await error_logger.log_error(f"🆘 {error_msg}")
    finally:
        await error_logger.log_error("🔴 Бот остановлен")
        logger.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())