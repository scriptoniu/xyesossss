import asyncio
from io import BytesIO
import regex as re
import requests
from telethon import TelegramClient, events
from telethon.tl import functions
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from concurrent.futures import ThreadPoolExecutor
from config import *
import socks
import random
from telethon.errors import SessionPasswordNeededError

# ========== Глобальные переменные ==========
checks = []
wallet = []
channels = []
captches = []
checks_count = 0
client = None  # Будет инициализирован в main()

# ========== Настройка прокси ==========
def load_proxies(file_path='proxies.txt'):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_proxy():
    proxy_list = load_proxies()
    proxy_line = random.choice(proxy_list)
    print(f"[PROXY] Используется: {proxy_line}")
    parts = proxy_line.split(':')
    if len(parts) == 2:
        return (socks.SOCKS5, parts[0], int(parts[1]))
    elif len(parts) == 4:
        return (socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3])
    raise ValueError(f"Неверный формат прокси: {proxy_line}")

# ========== Инициализация клиента ==========
async def create_client():
    proxy = get_proxy()
    return TelegramClient(
        session='cb_session',
        api_id=api_id,
        api_hash=api_hash,
        proxy=proxy,
        system_version="4.16.30-vxSOSYNXA"
    )

# ========== Вспомогательные функции ==========
code_regex = re.compile(r"t\.me/(CryptoBot|send|tonRocketBot|CryptoTestnetBot|wallet|xrocket|xJetSwapBot)\?start=(CQ[A-Za-z0-9]{10}|C-[A-Za-z0-9]{10}|t_[A-Za-z0-9]{15}|mci_[A-Za-z0-9]{15}|c_[a-z0-9]{24})", re.IGNORECASE)
url_regex = re.compile(r"https:\/\/t\.me\/\+(\w{12,})")
public_regex = re.compile(r"https:\/\/t\.me\/(\w{4,})")

replace_chars = ''' @#&+()*"'…;,!№•—–·±<{>}†★‡„“”«»‚‘’‹›¡¿‽~`|√π÷×§∆\\°^%©®™✓₤$₼€₸₾₶฿₳₥₦₫₿¤₲₩₮¥₽₻₷₱₧£₨¢₠₣₢₺₵₡₹₴₯₰₪'''
translation = str.maketrans('', '', replace_chars)

executor = ThreadPoolExecutor(max_workers=5)

# ========== OCR функция ==========
def ocr_space_sync(file: bytes):
    payload = {
        'isOverlayRequired': False,
        'apikey': ocr_api_key,
        'language': 'eng',
        'OCREngine': 2
    }
    response = requests.post(
        'https://api.ocr.space/parse/image',
        data=payload,
        files={'filename': ('image.png', file, 'image/png')}
    )
    return response.json().get('ParsedResults')[0].get('ParsedText').replace(" ", "")

async def ocr_space(file: bytes):
    return await asyncio.get_event_loop().run_in_executor(executor, ocr_space_sync, file)

# ========== Автовывод средств ==========
async def pay_out():
    while True:
        await asyncio.sleep(86400)
        try:
            await client.send_message('CryptoBot', '/wallet')
            await asyncio.sleep(0.1)
            msg = (await client.get_messages('CryptoBot', limit=1))[0].message
            for line in msg.split('\n\n'):
                if ':' in line:
                    data = line.split(': ')[1].split(' (')[0].split(' ')
                    if data[0] != '0':
                        try:
                            result = (await client.inline_query('send', f'{data[0]} {data[1]}'))[0]
                            if 'Создать чек' in result.title:
                                await result.click(avto_vivod_tag)
                        except:
                            pass
        except Exception as e:
            print(f"Ошибка автовывода: {e}")

# ========== Обработчики сообщений ==========
def register_handlers():
    @client.on(events.NewMessage(outgoing=True, pattern='.spam'))
    async def spam_handler(event):
        args = event.message.message.split(' ')
        for _ in range(int(args[1])):
            await event.respond(args[2])

    @client.on(events.NewMessage(chats=[1985737506], pattern="⚠️ Вы не можете активировать этот чек"))
    async def subscription_handler(event):
        global wallet
        try:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    if check := code_regex.search(button.url):
                        if (code := check.group(2)) not in wallet:
                            await client.send_message('wallet', f'/start {code}')
                            wallet.append(code)
                    if channel := url_regex.search(button.url):
                        await client(ImportChatInviteRequest(channel.group(1)))
        except Exception as e:
            print(f"Ошибка обработки подписки: {e}")

    @client.on(events.NewMessage(chats=crypto_black_list))
    async def check_handler(event):
        global checks, checks_count
        try:
            # Обработка чеков
            message_text = event.message.text.translate(translation)
            if codes := code_regex.findall(message_text):
                for bot_name, code in codes:
                    if code not in checks:
                        await client.send_message(bot_name, f'/start {code}')
                        checks.append(code)
            
            # Обработка уведомлений о получении средств
            for phrase in ['Вы получили', 'Вы обналичили чек', '✅ Вы получили']:
                if phrase in event.message.text:
                    try:
                        bot = (await client.get_entity(event.message.peer_id.user_id)).username
                        amount = event.message.text.split('\n')[0].split(phrase)[1].strip()
                        checks_count += 1
                        await client.send_message(
                            channel,
                            f'✅ Активирован чек: {amount}\nБот: @{bot}\nВсего чеков: {checks_count}',
                            parse_mode='HTML'
                        )
                    except:
                        pass
        except Exception as e:
            print(f"Ошибка обработки чека: {e}")

    if anti_captcha:
        @client.on(events.NewMessage(chats=[1559501630], func=lambda e: e.photo))
        async def captcha_handler(event):
            try:
                photo = await event.download_media(bytes)
                text = await ocr_space(photo)
                if text:
                    await client.send_message('CryptoBot', text)
            except Exception as e:
                print(f"Ошибка обработки капчи: {e}")

# ========== Основная функция ==========
async def main():
    global client
    client = await create_client()
    
    try:
        if not await client.is_user_authorized():
            print("\n--- Требуется авторизация ---")
            await client.start(
                phone=lambda: input("Введите номер (+7XXX...): "),
                code_callback=lambda: input("Код из Telegram/SMS: "),
                password=lambda: input("Пароль 2FA (если есть): "),
                max_attempts=3
            )
        else:
            await client.connect()
            print("✅ Используется сохраненная сессия")

        register_handlers()
        
        try:
            await client(JoinChannelRequest('lovec_checkov'))
        except:
            pass

        if avto_vivod and avto_vivod_tag:
            asyncio.create_task(pay_out())
            print(f"💰 Автовывод на тег: {avto_vivod_tag}")

        print("🟢 Бот запущен и работает")
        await client.run_until_disconnected()

    except SessionPasswordNeededError:
        print("🔐 Требуется пароль 2FA! Удалите файл сессии и перезапустите.")
    except Exception as e:
        print(f"🔴 Критическая ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())