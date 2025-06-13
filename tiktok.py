import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher.filters import CommandStart
from aiogram.contrib.middlewares.logging import LoggingMiddleware

API_TOKEN = '7755541704:AAGkzAZZ-Sigl4SF8dw8UUtGO1HD4oeMews'  # Замени на свой токен

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


def get_tiktok_data(url):
    api_url = f"https://tikwm.com/api/?url={url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    return None


@dp.message_handler(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Отправь мне ссылку на TikTok-видео, и я скачаю его без водяного знака!")


@dp.message_handler(lambda message: 'tiktok.com' in message.text or 'vt.tiktok.com' in message.text)
async def handle_tiktok(message: types.Message):
    await message.answer("⏳ Обрабатываю...")

    result = get_tiktok_data(message.text)
    if not result or result.get("code") != 0:
        await message.answer("❌ Не удалось обработать ссылку. Проверь её и попробуй ещё раз.")
        return

    data = result["data"]

    if "images" in data and data["images"]:
        # Пост с изображениями (фото или карусель)
        for img_url in data["images"]:
            await message.answer_photo(img_url)
        await message.answer("✅ Вот твои изображения без водяного знака.")
    elif "play" in data and data["play"]:
        # Видео
        await message.answer_video(data["play"])
        await message.answer("✅ Вот твоё видео без водяного знака.")
    else:
        await message.answer("⚠️ Не удалось найти видео или изображения.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)