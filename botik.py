import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Настройки
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация (оставляем прямо в коде, как вы просили)
BOT_TOKEN = "7755541704:AAHINZn-mtLddqc7RJV1VHCpE6AbAzwAAuI"
ADMIN_IDS = {7091921882, 123456789}  # Теперь несколько админов
ALLOWED_USERS = {*ADMIN_IDS, 987654321}  # Админы + другие разрешенные пользователи
CHATS_FILE = "target_chats.txt"
IGNORED_USERS_FILE = "ignored_users.txt"
TRACKING_ENABLED = True

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

def load_chats():
    """Загружает список чатов с проверкой формата"""
    chats = {}
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    chat_id, name = parts
                    chats[chat_id] = {"name": name, "is_open": True}
                else:
                    logger.warning(f"Некорректная строка в {CHATS_FILE}: {line}")
    except FileNotFoundError:
        logger.warning(f"Файл {CHATS_FILE} не найден, создан новый")
    except Exception as e:
        logger.error(f"Ошибка загрузки чатов: {e}")
    return chats

def save_chats(chats):
    """Сохраняет чаты в файл"""
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            for chat_id, info in chats.items():
                f.write(f"{chat_id} {info['name']}\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения чатов: {e}")

def load_ignored_users():
    """Загружает список игнорируемых пользователей"""
    try:
        with open(IGNORED_USERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки игнорируемых: {e}")
        return []

async def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return str(user_id) in map(str, ADMIN_IDS)

async def is_allowed(user_id):
    """Проверяет, есть ли у пользователя доступ к боту"""
    return str(user_id) in map(str, ALLOWED_USERS)

async def set_chat_permissions(chat_id, is_open):
    """Устанавливает права чата с обработкой ошибок"""
    try:
        await bot.set_chat_permissions(
            int(chat_id),
            types.ChatPermissions(
                can_send_messages=is_open,
                can_send_media_messages=is_open,
                can_send_other_messages=is_open,
                can_add_web_page_previews=is_open
            )
        )
        return True
    except Exception as e:
        logger.error(f"Не удалось изменить права в чате {chat_id}: {e}")
        return False

async def get_actual_chats():
    """Возвращает только те чаты, где бот является администратором"""
    chats = load_chats()
    actual_chats = {}
    
    for chat_id in chats:
        try:
            chat_member = await bot.get_chat_member(int(chat_id), bot.id)
            if chat_member.status in ["administrator", "creator"]:
                actual_chats[chat_id] = chats[chat_id]
        except Exception as e:
            logger.warning(f"Бот не является участником чата {chat_id} или нет прав: {e}")
    
    return actual_chats

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if not await is_allowed(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этому боту")
        return
    
    text = (
        "🤖 <b>Бот управления чатами</b>\n\n"
        "🔹 <code>/chats</code> - список чатов\n"
        "🔹 <code>/manage</code> - управление доступом\n"
        "🔹 <code>/tracking</code> - вкл/выкл отслеживание\n"
        "🔹 <code>/ignored</code> - список игнорируемых"
    )
    
    if await is_admin(message.from_user.id):
        text += "\n\n⚙️ <i>Вы администратор этого бота</i>"
    
    await message.answer(text)

@dp.message(Command("manage"))
async def cmd_manage(message: types.Message):
    """Управление доступом в чатах"""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Только администраторы могут управлять чатами")
        return

    actual_chats = await get_actual_chats()
    if not actual_chats:
        await message.answer("🤷‍♂️ Бот не является админом ни в одном из чатов")
        return

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
            for chat_id, info in actual_chats.items()
        ]
    ])

    await message.answer(
        "⚙️ <b>Управление чатами (только с админ-правами):</b>\n"
        "🔓 - чат открыт\n"
        "🔒 - чат закрыт",
        reply_markup=keyboard
    )

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    """Обработка нажатий кнопок"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Недостаточно прав", show_alert=True)
        return

    actual_chats = await get_actual_chats()
    data = callback.data
    success_count = 0

    try:
        if data in ["open_all", "close_all"]:
            is_open = data == "open_all"
            for chat_id in actual_chats:
                if await set_chat_permissions(chat_id, is_open):
                    actual_chats[chat_id]["is_open"] = is_open
                    success_count += 1
            
            save_chats(actual_chats)
            await callback.answer(
                f"Успешно {'открыто' if is_open else 'закрыто'} {success_count}/{len(actual_chats)} чатов",
                show_alert=True
            )

        elif data.startswith("toggle:"):
            chat_id = data.split(":")[1]
            if chat_id in actual_chats:
                is_open = not actual_chats[chat_id]["is_open"]
                if await set_chat_permissions(chat_id, is_open):
                    actual_chats[chat_id]["is_open"] = is_open
                    save_chats(actual_chats)
                    await callback.answer(f"Чат {'открыт' if is_open else 'закрыт'}")
                else:
                    await callback.answer("❌ Ошибка изменения прав", show_alert=True)
            else:
                await callback.answer("❌ Чат не найден", show_alert=True)

        await cmd_manage(callback.message)
    except Exception as e:
        logger.error(f"Ошибка в process_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

# Остальные обработчики (/chats, /tracking, /ignored) остаются аналогичными предыдущим версиям
# ...

@dp.message()
async def handle_message(message: types.Message):
    """Обработка всех сообщений"""
    if not await is_allowed(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этому боту")
        return
    
    # Остальная логика обработки сообщений
    await track_message(message)

async def track_message(message: types.Message):
    """Отслеживание сообщений"""
    if not TRACKING_ENABLED:
        return

    if not await is_admin(message.from_user.id) and str(message.from_user.id) not in load_ignored_users():
        chat_id = str(message.chat.id)
        chats = load_chats()
        
        if chat_id in chats:
            user = message.from_user
            chat = message.chat
            
            if chat.username:
                message_link = f"https://t.me/{chat.username}/{message.message_id}"
            else:
                message_link = f"https://t.me/c/{str(abs(int(chat.id)))[4:]}/{message.message_id}" if str(chat.id).startswith("-100") else f"chat_id: {chat.id}"

            text = (
                f"📨 <b>Новое сообщение</b>\n"
                f"👤 <b>От:</b> {user.full_name} (@{user.username or 'нет'})\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                f"💬 <b>Чат:</b> {chat.title}\n"
                f"🔗 <a href='{message_link}'>Ссылка на сообщение</a>\n\n"
                f"📝 <b>Текст:</b>\n<code>{message.text or 'Медиа-сообщение'}</code>"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, text)
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление admin {admin_id}: {e}")

async def main():
    """Основная функция"""
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Ошибка запуска бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())