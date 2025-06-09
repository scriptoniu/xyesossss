import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # ← добавлено

# Настройки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7755541704:AAHINZn-mtLddqc7RJV1VHCpE6AbAzwAAuI"
ADMIN_ID = 7091921882
CHATS_FILE = "chats.txt"
IGNORED_USERS_FILE = "ignored_users.txt"
TRACKING_ENABLED = True

# ✅ исправлено: parse_mode теперь указывается через DefaultBotProperties
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ========================
# Функции работы с файлами
# ========================
def load_chats():
    """Загружает список чатов из файла"""
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return {line.split()[0]: {"name": " ".join(line.split()[1:]), "is_open": True} 
                   for line in f if line.strip()}
    except FileNotFoundError:
        return {}

def save_chats(chats):
    """Сохраняет чаты в файл"""
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        for chat_id, info in chats.items():
            f.write(f"{chat_id} {info['name']}\n")

def load_ignored_users():
    """Загружает список игнорируемых пользователей"""
    try:
        with open(IGNORED_USERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_ignored_users(users):
    """Сохраняет игнорируемых пользователей"""
    with open(IGNORED_USERS_FILE, "w") as f:
        f.write("\n".join(users))

async def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return str(user_id) == str(ADMIN_ID)

async def set_chat_permissions(chat_id, is_open):
    """Устанавливает права чата"""
    await bot.set_chat_permissions(
        chat_id,
        types.ChatPermissions(
            can_send_messages=is_open,
            can_send_media_messages=is_open,
            can_send_other_messages=is_open,
            can_add_web_page_previews=is_open
        )
    )

# =================
# Команды бота
# =================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if not await is_admin(message.from_user.id):
        return
    
    await message.reply(
        "🤖 <b>Бот управления чатами</b>\n\n"
        "🔹 <code>/chats</code> - список чатов\n"
        "🔹 <code>/manage</code> - управление доступом\n"
        "🔹 <code>/tracking</code> - вкл/выкл отслеживание\n"
        "🔹 <code>/ignored</code> - список игнорируемых\n\n"
        "ℹ️ Чаты добавляются вручную в <code>chats.txt</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("chats"))
async def cmd_chats(message: types.Message):
    """Показывает список чатов"""
    if not await is_admin(message.from_user.id):
        return

    chats = load_chats()
    if not chats:
        await message.reply("📭 Список чатов пуст")
        return

    text = "📋 <b>Список чатов:</b>\n\n" + "\n".join(
        f"{'🔓' if info['is_open'] else '🔒'} {info['name']} (<code>{chat_id}</code>)"
        for chat_id, info in chats.items()
    )
    await message.reply(text, parse_mode=ParseMode.HTML)

@dp.message(Command("manage"))
async def cmd_manage(message: types.Message):
    """Управление доступом в чатах"""
    if not await is_admin(message.from_user.id):
        return

    chats = load_chats()
    if not chats:
        await message.reply("Нет добавленных чатов")
        return

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔓 Открыть все", callback_data="open_all"),
            InlineKeyboardButton(text="🔒 Закрыть все", callback_data="close_all")
        ],
        *[
            [InlineKeyboardButton(
                text=f"{'🔓' if info['is_open'] else '🔒'} {info['name'][:15]}...",
                callback_data=f"toggle:{chat_id}"
            )]
            for chat_id, info in chats.items()
        ]
    ])

    await message.reply(
        "⚙️ <b>Управление чатами:</b>\n"
        "🔓 - чат открыт\n"
        "🔒 - чат закрыт",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("tracking"))
async def cmd_tracking(message: types.Message):
    """Включает/выключает отслеживание"""
    if not await is_admin(message.from_user.id):
        return

    global TRACKING_ENABLED
    TRACKING_ENABLED = not TRACKING_ENABLED
    status = "✅ Включено" if TRACKING_ENABLED else "❌ Выключено"
    await message.reply(f"Отслеживание сообщений: <b>{status}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("ignored"))
async def cmd_ignored(message: types.Message):
    """Показывает игнорируемых пользователей"""
    if not await is_admin(message.from_user.id):
        return

    ignored = load_ignored_users()
    if not ignored:
        await message.reply("📭 Список игнорируемых пуст")
        return

    await message.reply(
        "👥 <b>Игнорируемые пользователи:</b>\n" + "\n".join(f"• <code>{user_id}</code>" for user_id in ignored),
        parse_mode=ParseMode.HTML
    )

# ======================
# Обработчики событий
# ======================
@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    """Обрабатывает нажатия кнопок"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    chats = load_chats()
    data = callback.data

    try:
        if data in ["open_all", "close_all"]:
            # Массовое открытие/закрытие чатов
            is_open = data == "open_all"
            for chat_id in chats:
                chats[chat_id]["is_open"] = is_open
                await set_chat_permissions(int(chat_id), is_open)
            await callback.answer(f"Все чаты {'открыты' if is_open else 'закрыты'}")

        elif data.startswith("toggle:"):
            # Переключение конкретного чата
            chat_id = data.split(":")[1]
            if chat_id in chats:
                is_open = not chats[chat_id]["is_open"]
                chats[chat_id]["is_open"] = is_open
                await set_chat_permissions(int(chat_id), is_open)
                await callback.answer(f"Чат {'открыт' if is_open else 'закрыт'}")

        # Обновляем сообщение с кнопками
        await cmd_manage(callback.message)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка")

@dp.message()
async def track_message(message: types.Message):
    """Отслеживает новые сообщения"""
    if not TRACKING_ENABLED:
        return

    # Проверяем права и игнор-лист
    if (not await is_admin(message.from_user.id) and 
        str(message.from_user.id) not in load_ignored_users() and
        str(message.chat.id) in load_chats()):

        user = message.from_user
        chat = message.chat
        
        # Формируем ссылку на сообщение
        if chat.username:
            message_link = f"https://t.me/{chat.username}/{message.message_id}"
        else:
            message_link = (
                f"https://t.me/c/{str(abs(chat.id))[4:]}/{message.message_id}"
                if str(chat.id).startswith("-100")
                else f"chat_id: {chat.id}"
            )

        # Отправляем уведомление
        await bot.send_message(
            ADMIN_ID,
            f"📨 <b>Новое сообщение</b>\n"
            f"👤 <b>От:</b> {user.full_name} (@{user.username or 'нет'})\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"💬 <b>Чат:</b> {chat.title}\n"
            f"🔗 <a href='{message_link}'>Ссылка на сообщение</a>\n\n"
            f"📝 <b>Текст:</b>\n<code>{message.text or 'Медиа-сообщение'}</code>",
            parse_mode=ParseMode.HTML
        )

# ========
# Запуск
# ========
async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())