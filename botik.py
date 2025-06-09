import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = "7755541704:AAHINZn-mtLddqc7RJV1VHCpE6AbAzwAAuI"  # Замените на реальный токен!
ADMIN_ID = 7091921882  # Ваш Telegram ID
CHATS_FILE = "chats.txt"
IGNORED_USERS_FILE = "ignored_users.txt"
TRACKING_ENABLED = True

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загрузка списка чатов (из txt)
def load_chats():
    try:
        with open(CHATS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# Загрузка игнорируемых пользователей (из txt)
def load_ignored_users():
    try:
        with open(IGNORED_USERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def is_admin(user_id):
    return user_id == ADMIN_ID

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.reply("⚠️ Бот доступен только администратору")
        return
    await message.reply(
        "🤖 Упрощенный бот для мониторинга чатов\n\n"
        "ℹ️ Чаты и игнор-лист редактируются вручную:\n"
        f"- Чаты: {CHATS_FILE}\n"
        f"- Игнор: {IGNORED_USERS_FILE}\n\n"
        "Команды:\n"
        "/tracking - вкл/выкл отслеживание\n"
        "/chats - показать текущие чаты\n"
        "/ignored - показать игнорируемых"
    )

# Команда /tracking (включить/выключить мониторинг)
@dp.message(Command("tracking"))
async def cmd_tracking(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    global TRACKING_ENABLED
    TRACKING_ENABLED = not TRACKING_ENABLED
    status = "✅ Включено" if TRACKING_ENABLED else "❌ Выключено"
    await message.reply(f"Отслеживание сообщений: {status}")

# Команда /chats (показать чаты)
@dp.message(Command("chats"))
async def cmd_chats(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    chats = load_chats()
    if not chats:
        await message.reply("📭 Список чатов пуст.")
        return

    await message.reply("📋 Текущие чаты:\n" + "\n".join(chats))

# Команда /ignored (показать игнорируемых)
@dp.message(Command("ignored"))
async def cmd_ignored(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    ignored_users = load_ignored_users()
    if not ignored_users:
        await message.reply("📭 Список игнорируемых пуст.")
        return

    await message.reply("📋 Игнорируемые пользователи:\n" + "\n".join(ignored_users))

# Отслеживание новых сообщений
@dp.message()
async def track_message(message: types.Message):
    if not TRACKING_ENABLED:
        return

    if not await is_admin(message.from_user.id):
        # Проверяем, находится ли пользователь в игнор-листе
        if str(message.from_user.id) in load_ignored_users():
            return

        # Проверяем, отслеживается ли чат
        if str(message.chat.id) not in load_chats():
            return

        # Формируем уведомление
        user = message.from_user
        chat = message.chat
        message_link = (
            f"https://t.me/{chat.username}/{message.message_id}"
            if chat.username
            else f"Сообщение в чате (ID: {chat.id})"
        )
        text = (
            f"📨 Новое сообщение:\n"
            f"👤 От: @{user.username or user.first_name} (ID: {user.id})\n"
            f"💬 Чат: {chat.title or 'Без названия'}\n"
            f"🔗 Ссылка: {message_link}\n"
            f"📝 Текст: {message.text or 'Нет текста (возможно, медиа)'}"
        )
        await bot.send_message(ADMIN_ID, text)

async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
