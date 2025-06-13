import logging
import requests
import re
from aiogram import Bot, Dispatcher, types, executor

# === Твой токен от BotFather ===
API_TOKEN = '7755541704:AAGkzAZZ-Sigl4SF8dw8UUtGO1HD4oeMews'

# === Настройка логирования и инициализация бота ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === Проверка ссылки TikTok ===
def is_valid_tiktok_url(url):
    return re.match(r'https?://(vm\.tiktok\.com|www\.tiktok\.com)/', url)

# === TikWM API: получаем прямую ссылку на видео без водяного знака ===
def get_video_url(tiktok_url):
    api_url = 'https://tikwm.com/api/'
    try:
        resp = requests.get(api_url, params={'url': tiktok_url}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["play"]  # Ссылка на видео без водяка
        else:
            return None
    except Exception as e:
        print(f"Ошибка запроса к API: {e}")
        return None

# === /start ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привет! Пришли мне ссылку на TikTok, и я скачаю видео без водяного знака 🎬")

# === Обработка сообщений с TikTok-ссылками ===
@dp.message_handler()
async def download_handler(message: types.Message):
    url = message.text.strip()

    if not is_valid_tiktok_url(url):
        await message.reply("❗ Это не похоже на ссылку TikTok. Попробуй ещё раз.")
        return

    await message.reply("⏳ Обрабатываю ссылку...")

    video_url = get_video_url(url)
    if video_url:
        try:
            await bot.send_video(chat_id=message.chat.id, video=video_url, caption="✅ Вот твоё видео без водяного знака")
        except:
            await message.reply(f"⚠️ Не удалось отправить видео (возможно, слишком большое). Вот ссылка:\n{video_url}")
    else:
        await message.reply("❌ Не удалось скачать видео. Попробуй позже.")

# === Запуск ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
