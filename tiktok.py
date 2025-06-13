import logging
import requests
import re
import os
import mimetypes
import tempfile
from aiogram import Bot, Dispatcher, types, executor

# === 🔑 Твой API токен ===
API_TOKEN = '7755541704:AAGkzAZZ-Sigl4SF8dw8UUtGO1HD4oeMews'

# === ⚙️ Настройка ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# === Проверка ссылки TikTok ===
def is_valid_tiktok_url(url):
    return re.match(r'https?://(vm\.tiktok\.com|vt\.tiktok\.com|www\.tiktok\.com)/', url)

# === Разворачиваем короткую ссылку (если нужно) ===
def expand_short_url(url):
    try:
        session = requests.Session()
        response = session.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        print(f"[expand_short_url] Ошибка: {e}")
        return url

# === Получение данных через TikWM API ===
def get_media_data(tiktok_url):
    api_url = 'https://tikwm.com/api/'
    try:
        resp = requests.get(api_url, params={'url': tiktok_url}, timeout=10)
        data = resp.json()

        if data.get("code") != 0:
            print(f"[get_media_data] Ошибка TikWM: {data}")
            return None

        result = data["data"]
        if result.get("play"):
            return {"type": "video", "url": result["play"]}

        if result.get("images") and isinstance(result["images"], list):
            return {"type": "images", "urls": result["images"]}

        print(f"[get_media_data] Нет видео или фото. Ответ: {result}")
        return None

    except Exception as e:
        print(f"[get_media_data] Ошибка запроса: {e}")
        return None

# === Отправка изображений как альбома ===
async def send_images(chat_id, urls):
    files = []
    try:
        for i, url in enumerate(urls[:10]):
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                ext = mimetypes.guess_extension(response.headers['Content-Type']) or '.jpg'
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_file.write(response.content)
                tmp_file.close()
                files.append(tmp_file.name)

        media = [types.InputMediaPhoto(types.InputFile(f)) for f in files]
        await bot.send_media_group(chat_id=chat_id, media=media)
    except Exception as e:
        print(f"[send_images] Ошибка: {e}")
        await bot.send_message(chat_id, "⚠️ Ошибка при отправке изображений.")
    finally:
        for f in files:
            try:
                os.unlink(f)
            except:
                pass

# === Команда /start ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("👋 Привет! Отправь мне ссылку на TikTok — я скачаю видео или изображения без водяного знака!")

# === Обработка сообщений с TikTok-ссылками ===
@dp.message_handler()
async def download_handler(message: types.Message):
    url = message.text.strip()

    if not is_valid_tiktok_url(url):
        await message.reply("❗ Это не похоже на TikTok-ссылку.")
        return

    await message.reply("🔄 Обрабатываю...")

    full_url = expand_short_url(url)
    media = get_media_data(full_url)

    if not media:
        await message.reply("❌ Не удалось скачать. Возможно, ссылка битая или пост приватный.")
        return

    if media["type"] == "video":
        try:
            await bot.send_video(chat_id=message.chat.id, video=media["url"], caption="✅ Вот твоё видео без водяного знака")
        except Exception as e:
            print(f"[send_video] Ошибка: {e}")
            await message.reply(f"⚠️ Не удалось отправить видео. Вот ссылка:\n{media['url']}")

    elif media["type"] == "images":
        await send_images(message.chat.id, media["urls"])
        await message.reply("📷 Вот изображения из TikTok-поста")

# === Запуск ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)