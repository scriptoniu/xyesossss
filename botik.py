import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7755541704:AAHINZn-mtLddqc7RJV1VHCpE6AbAzwAAuI"
ADMIN_ID = 7091921882
CHATS_FILE = "chats.txt"
IGNORED_USERS_FILE = "ignored_users.txt"
TRACKING_ENABLED = True

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функции работы с файлами
def load_chats():
    try:
        with open(CHATS_FILE, "r") as f:
            return {line.split()[0]: {"name": " ".join(line.split()[1:]), "is_open": True} 
                   for line in f if line.strip()}
    except FileNotFoundError:
        return {}

def save_chats(chats):
    with open(CHATS_FILE, "w") as f:
        for chat_id, info in chats.items():
            f.write(f"{chat_id} {info['name']}\n")

def load_ignored_users():
    try:
        with open(IGNORED_USERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

async def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# Команды управления
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    await message.reply(
        "🤖 Бот управления чатами\n\n"
        "Команды:\n"
        "/chats - список чатов\n"
        "/manage - управление доступом\n"
        "/tracking - вкл/выкл отслеживание\n"
        "/ignored - список игнора"
    )

@dp.message(Command("manage"))
async def cmd_manage(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    chats = load_chats()
    if not chats:
        await message.reply("Нет добавленных чатов")
        return

    keyboard = [
        [
            InlineKeyboardButton(text="🔓 Открыть все", callback_data="open_all"),
            InlineKeyboardButton(text="🔒 Закрыть все", callback_data="close_all")
        ]
    ]
    
    for chat_id, info in chats.items():
        status = "🔓" if info.get("is_open", True) else "🔒"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {info['name'][:15]}...",
                callback_data=f"toggle:{chat_id}"
            )
        ])

    await message.reply(
        "⚙️ Управление чатами:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    chats = load_chats()
    data = callback.data

    try:
        if data in ["open_all", "close_all"]:
            is_open = data == "open_all"
            for chat_id in chats:
                chats[chat_id]["is_open"] = is_open
                await set_chat_permissions(int(chat_id), is_open)
            save_chats(chats)
            await callback.answer("✅ Готово")

        elif data.startswith("toggle:"):
            chat_id = data.split(":")[1]
            if chat_id in chats:
                is_open = not chats[chat_id].get("is_open", True)
                chats[chat_id]["is_open"] = is_open
                await set_chat_permissions(int(chat_id), is_open)
                save_chats(chats)
                await callback.answer("✅ Готово")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка")

    await update_manage_message(callback.message)

async def set_chat_permissions(chat_id, is_open):
    await bot.set_chat_permissions(
        chat_id,
        types.ChatPermissions(
            can_send_messages=is_open,
            can_send_media_messages=is_open,
            can_send_other_messages=is_open,
            can_add_web_page_previews=is_open
        )
    )

async def update_manage_message(message: types.Message):
    await cmd_manage(message)

# Отслеживание сообщений с улучшенными уведомлениями
@dp.message()
async def track_message(message: types.Message):
    if not TRACKING_ENABLED:
        return

    if not await is_admin(message.from_user.id):
        if str(message.from_user.id) in load_ignored_users():
            return

        chat_id = str(message.chat.id)
        chats = load_chats()
        if chat_id not in chats:
            return

        user = message.from_user
        chat = message.chat
        
        # Формируем ссылку на сообщение
        if chat.username:
            message_link = f"https://t.me/{chat.username}/{message.message_id}"
        else:
            # Для приватных чатов - альтернативный вариант
            message_link = (
                f"https://t.me/c/{str(chat.id).replace('-100', '')}/{message.message_id}"
                if str(chat.id).startswith("-100")
                else f"Чат ID: {chat.id}"
            )

        text = (
            f"📨 Новое сообщение\n"
            f"👤 От: {user.full_name} (@{user.username})\n"
            f"🆔 ID: {user.id}\n"
            f"💬 Чат: {chat.title}\n"
            f"🔗 Ссылка: {message_link}\n\n"
            f"📝 Текст: {message.text or 'Медиа-сообщение'}"
        )
        
        await bot.send_message(ADMIN_ID, text)

# Остальные команды (/chats, /ignored, /tracking) остаются без изменений
# ...

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())