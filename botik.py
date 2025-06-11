import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Настройки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7408741591:AAFRnWBMc1Cdd2cfjRpljzAjcf9k8dN24zI"
ADMIN_ID = 7091921882
CHATS_FILE = "target_chats.txt"
IGNORED_USERS_FILE = "ignored_users.txt"
TRACKING_ENABLED = True

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ======== Работа с файлами ========
def load_chats():
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return {
                line.split()[0]: {"name": " ".join(line.split()[1:]), "is_open": True}
                for line in f if line.strip()
            }
    except FileNotFoundError:
        return {}

def save_chats(chats):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        for chat_id, info in chats.items():
            f.write(f"{chat_id} {info['name']}\n")

def load_ignored_users():
    try:
        with open(IGNORED_USERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_ignored_users(users):
    with open(IGNORED_USERS_FILE, "w") as f:
        f.write("\n".join(users))

async def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

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

# ======== Команды ========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    await message.reply(
        "🤖 <b>Бот управления чатами</b>\n\n"
        "🔹 <code>/chats</code> - список чатов\n"
        "🔹 <code>/manage</code> - управление доступом\n"
        "🔹 <code>/tracking</code> - вкл/выкл отслеживание\n"
        "🔹 <code>/ignored</code> - список игнорируемых\n\n"
        "ℹ️ Чаты добавляются вручную в <code>target_chats.txt</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("chats"))
async def cmd_chats(message: types.Message):
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
    if not await is_admin(message.from_user.id):
        return

    chats = load_chats()
    if not chats:
        await message.reply("Нет добавленных чатов")
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
    if not await is_admin(message.from_user.id):
        return

    global TRACKING_ENABLED
    TRACKING_ENABLED = not TRACKING_ENABLED
    status = "✅ Включено" if TRACKING_ENABLED else "❌ Выключено"
    await message.reply(f"Отслеживание сообщений: <b>{status}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("ignored"))
async def cmd_ignored(message: types.Message):
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

# ======== Callback обработка ========
@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен")
        return

    chats = load_chats()
    data = callback.data
    updated_count = 0
    total_attempted = 0

    try:
        if data in ["open_all", "close_all"]:
            is_open = data == "open_all"
            for chat_id in chats:
                total_attempted += 1
                try:
                    member = await bot.get_chat_member(chat_id=int(chat_id), user_id=bot.id)
                    if member.status in ["administrator", "creator"]:
                        chats[chat_id]["is_open"] = is_open
                        await set_chat_permissions(int(chat_id), is_open)
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Не удалось изменить чат {chat_id}: {e}")

            await callback.answer(f"✅ {updated_count}/{total_attempted} чатов {'открыто' if is_open else 'закрыто'}")

        elif data.startswith("toggle:"):
            chat_id = data.split(":")[1]
            if chat_id in chats:
                try:
                    member = await bot.get_chat_member(chat_id=int(chat_id), user_id=bot.id)
                    if member.status in ["administrator", "creator"]:
                        is_open = not chats[chat_id]["is_open"]
                        chats[chat_id]["is_open"] = is_open
                        await set_chat_permissions(int(chat_id), is_open)
                        await callback.answer(f"Чат {'открыт' if is_open else 'закрыт'}")
                    else:
                        await callback.answer("❌ Нет прав администратора")
                except Exception as e:
                    logger.warning(f"Ошибка в toggle-чате {chat_id}: {e}")
                    await callback.answer("❌ Не удалось изменить чат")

        save_chats(chats)
        await cmd_manage(callback.message)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка")

# ======== Трекинг сообщений ========
@dp.message()
async def track_message(message: types.Message):
    if not TRACKING_ENABLED:
        return

    if (
        not await is_admin(message.from_user.id) and
        str(message.from_user.id) not in load_ignored_users() and
        str(message.chat.id) in load_chats()
    ):
        user = message.from_user
        chat = message.chat

        try:
            if chat.username:
                message_link = f"https://t.me/{chat.username}/{message.message_id}"
            elif str(chat.id).startswith("-100"):
                channel_id = str(chat.id)[4:]
                message_link = f"https://t.me/c/{channel_id}/{message.message_id}"
            else:
                message_link = f"tg://openmessage?chat_id={chat.id}&message_id={message.message_id}"
        except Exception as e:
            logger.error(f"Ошибка генерации ссылки: {e}")
            message_link = "Не удалось создать ссылку"

        text = (
            f"📨 <b>Новое сообщение</b>\n"
            f"👤 <b>От:</b> {user.full_name} (@{user.username or 'нет'})\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"💬 <b>Чат:</b> {chat.title or 'Без названия'}\n"
            f"🔗 <a href='{message_link}'>Ссылка на сообщение</a>\n\n"
            f"📝 <b>Текст:</b>\n<code>{message.text or 'Медиа-сообщение'}</code>"
        )

        try:
            await bot.send_message(
                ADMIN_ID,
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Ошибка отправки администратору: {e}")

# ======== Запуск ========
async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())