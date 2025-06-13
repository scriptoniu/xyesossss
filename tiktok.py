import logging
import requests
import re
from aiogram import Bot, Dispatcher, types, executor

# === 🔑 Укажи свой токен от BotFather ===
API_TOKEN = '7755541704:AAGkzAZZ-Sigl4SF8dw8UUtGO1HD4oeMews'

# === ⚙️ Настройка логов и бота ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === 🔗 Проверка, TikTok ли это вообще ===
def is_valid_tiktok_url(url):
    return re.match(r'https?://(vm\.tiktok\.com|vt\.tiktok\.com|www\.tiktok\.com)/', url)

# === ↪️ Разворачиваем короткую ссылку (если нужно) ===
def expand_short_url(url):
    try:
        session = requests.Session()
        response = session.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        print(f"[expand_short_url] Ошибка: {e}")
        return url  # если не удалось — вернём как есть

# === 📥 Получение видео через TikWM API ===
def get_video_url(tiktok_url):
    api_url = 'https://tikwm.com/api/'
    try:
        resp = requests.get(api_url, params={'url': tiktok_url}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["play"]
        else:
            print(f"[get_video_url] TikWM ответ: {data}")
            return None
    except Exception as e:
        print(f"[get_video_url] Ошибка: {e}")
        return None

# === /start команда ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привет! Пришли мне ссылку на TikTok, и я скачаю видео без водяного знака 🎬")

# === Обработка сообщений ===
@dp.message_handler()
async def download_handler(message: types.Message):
    url = message.text.strip()

    if not is_valid_tiktok_url(url):
        await message.reply("❗ Это не похоже на ссылку TikTok. Пришли корректную ссылку.")
        return

    await message.reply("🔄 Обрабатываю...")

    full_url = expand_short_url(url)
    video_url = get_video_url(full_url)

    if video_url:
        try:
            await bot.send_video(chat_id=message.chat.id, video=video_url, caption="✅ Готово! Вот твоё видео без водяного знака")
        except Exception as e:
            print(f"[send_video] Ошибка: {e}")
            await message.reply(f"⚠️ Не удалось отправить видео (возможно, слишком большое). Вот ссылка:\n{video_url}")
    else:
        await message.reply("❌ Не удалось скачать видео. Возможно, оно приватное или TikTok изменил структуру ссылок.")

# === 🚀 Запуск ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)