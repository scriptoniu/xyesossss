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

# --- Proxy Setup ---
def load_proxies(file_path='proxies.txt'):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_proxy():
    proxy_list = load_proxies()
    proxy_line = random.choice(proxy_list)
    print(f"[PROXY] Подключение через: {proxy_line}")
    parts = proxy_line.split(':')
    if len(parts) == 2:
        return (socks.SOCKS5, parts[0], int(parts[1]))
    elif len(parts) == 4:
        return (socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3])
    else:
        raise ValueError(f"Неверный формат прокси: {proxy_line}")

# --- Client Initialization ---
async def create_client():
    proxy = get_proxy()
    client = TelegramClient(
        session='cb_session',
        api_id=api_id,
        api_hash=api_hash,
        proxy=proxy,
        system_version="4.16.30-vxSOSYNXA"
    )
    
    if not await client.is_user_authorized():
        print("\n--- Требуется авторизация ---")
        await client.start(
            phone=lambda: input("Введите номер телефона (+7XXX...): "),
            code_callback=lambda: input("Код из Telegram/SMS: "),
            password=lambda: input("Пароль 2FA (если есть): "),
            max_attempts=3
        )
    else:
        await client.connect()
        print("✅ Используется сохраненная сессия")
    
    return client

# --- Core Functions ---
code_regex = re.compile(r"t\.me/(CryptoBot|send|tonRocketBot|CryptoTestnetBot|wallet|xrocket|xJetSwapBot)\?start=(CQ[A-Za-z0-9]{10}|C-[A-Za-z0-9]{10}|t_[A-Za-z0-9]{15}|mci_[A-Za-z0-9]{15}|c_[a-z0-9]{24})", re.IGNORECASE)
url_regex = re.compile(r"https:\/\/t\.me\/\+(\w{12,})")
public_regex = re.compile(r"https:\/\/t\.me\/(\w{4,})")

replace_chars = ''' @#&+()*"'…;,!№•—–·±<{>}†★‡„“”«»‚‘’‹›¡¿‽~`|√π÷×§∆\\°^%©®™✓₤$₼€₸₾₶฿₳₥₦₫₿¤₲₩₮¥₽₻₷₱₧£₨¢₠₣₢₺₵₡₹₴₯₰₪'''
translation = str.maketrans('', '', replace_chars)

executor = ThreadPoolExecutor(max_workers=5)

crypto_black_list = [1622808649, 1559501630, 1985737506, 5014831088, 6014729293, 5794061503]

checks = []
wallet = []
channels = []
captches = []
checks_count = 0

# --- Handlers ---
@client.on(events.NewMessage(outgoing=True, pattern='.spam'))
async def handler(event):
    chat = event.chat if event.chat else (await event.get_chat())
    args = event.message.message.split(' ')
    for _ in range(int(args[1])):
        await client.send_message(chat, args[2])

def ocr_space_sync(file: bytes, overlay=False, language='eng', scale=True, OCREngine=2):
    payload = {
        'isOverlayRequired': overlay,
        'apikey': ocr_api_key,
        'language': language,
        'scale': scale,
        'OCREngine': OCREngine
    }
    response = requests.post(
        'https://api.ocr.space/parse/image',
        data=payload,
        files={'filename': ('image.png', file, 'image/png')}
    )
    result = response.json()
    return result.get('ParsedResults')[0].get('ParsedText').replace(" ", "")

async def ocr_space(file: bytes, overlay=False, language='eng'):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, ocr_space_sync, file, overlay, language)

async def pay_out():
    while True:
        await asyncio.sleep(86400)
        await client.send_message('CryptoBot', message='/wallet')
        await asyncio.sleep(0.1)
        messages = await client.get_messages('CryptoBot', limit=1)
        message = messages[0].message
        lines = message.split('\n\n')
        for line in lines:
            if ':' in line:
                if 'Доступно' in line:
                    data = line.split('\n')[2].split('Доступно: ')[1].split(' (')[0].split(' ')
                    summ, curency = data[0], data[1]
                else:
                    data = line.split(': ')[1].split(' (')[0].split(' ')
                    summ, curency = data[0], data[1]
                
                if summ != '0':
                    try:
                        result = (await client.inline_query('send', f'{summ} {curency}'))[0]
                        if 'Создать чек' in result.title:
                            await result.click(avto_vivod_tag)
                    except:
                        pass

# --- Message Handlers ---
@client.on(events.NewMessage(chats=[1985737506], pattern="⚠️ Вы не можете активировать этот чек, так как вы не являетесь подписчиком канала"))
async def handle_subscription(event):
    global wallet
    code = None
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    check = code_regex.search(button.url)
                    if check:
                        code = check.group(2)
                    
                    channel = url_regex.search(button.url)
                    public_channel = public_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await client(JoinChannelRequest(public_channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    
    if code and code not in wallet:
        await client.send_message('wallet', message=f'/start {code}')
        wallet.append(code)


@client.on(events.NewMessage(chats=[1559501630], pattern="Чтобы"))
async def handle_new_message(event):
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    channel = url_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    await event.message.click(data=b'check-subscribe')

@client.on(events.NewMessage(chats=[5014831088], pattern="Для активации чека"))
async def handle_new_message(event):
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    channel = url_regex.search(button.url)
                    public_channel = public_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await client(JoinChannelRequest(public_channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass
    await event.message.click(data=b'Check')

@client.on(events.NewMessage(chats=[5794061503]))
async def handle_new_message(event):
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    try:
                        if (button.data.decode()).startswith(('showCheque_', 'activateCheque_')):
                            await event.message.click(data=button.data)
                    except:
                        pass
                    channel = url_regex.search(button.url)
                    public_channel = public_regex.search(button.url)
                    if channel:
                        await client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await client(JoinChannelRequest(public_channel.group(1)))
                except:
                    pass
    except AttributeError:
        pass

async def filter(event):
    for word in ['Вы получили', 'Вы обналичили чек на сумму:', '✅ Вы получили:', '💰 Вы получили']:
        if word in event.message.text:
            return True
    return False

@client.on(events.MessageEdited(chats=crypto_black_list, func=filter))
@client.on(events.NewMessage(chats=crypto_black_list, func=filter))
async def handle_new_message(event):
    try:
        bot = (await client.get_entity(event.message.peer_id.user_id)).usernames[0].username
    except:
        bot = (await client.get_entity(event.message.peer_id.user_id)).username
    summ = event.raw_text.split('\n')[0].replace('Вы получили ', '').replace('✅ Вы получили: ', '').replace('💰 Вы получили ', '').replace('Вы обналичили чек на сумму: ', '')
    global checks_count
    checks_count += 1
    await client.send_message(channel, message=f'✅ Активирован чек на сумму <b>{summ}</b>\nБот: <b>@{bot}</b>\nВсего чеков после запуска активировано: <b>{checks_count}</b>', parse_mode='HTML') 

@client.on(events.MessageEdited(outgoing=False, chats=crypto_black_list, blacklist_chats=True))
@client.on(events.NewMessage(outgoing=False, chats=crypto_black_list, blacklist_chats=True))
async def handle_new_message(event):
    global checks
    message_text = event.message.text.translate(translation)
    codes = code_regex.findall(message_text)
    if codes:
        for bot_name, code in codes:
            if code not in checks:
                await client.send_message(bot_name, message=f'/start {code}')
                checks.append(code)
    try:
        for row in event.message.reply_markup.rows:
            for button in row.buttons:
                try:
                    match = code_regex.search(button.url)
                    if match:
                        if match.group(2) not in checks:
                            await client.send_message(match.group(1), message=f'/start {match.group(2)}')
                            checks.append(match.group(2))
                except AttributeError:
                    pass
    except AttributeError:
        pass

if anti_captcha == True:
    @client.on(events.NewMessage(chats=[1559501630], func=lambda e: e.photo))
    async def handle_photo_message(event):
        photo = await event.download_media(bytes)
        recognized_text = await ocr_space(file=photo)
        if recognized_text and recognized_text not in captches:
            await client.send_message('CryptoBot', message=recognized_text)
            await asyncio.sleep(0.1)
            message = (await client.get_messages('CryptoBot', limit=1))[0].message
            if 'Incorrect answer.' in message or 'Неверный ответ.' in message:
                await client.send_message(channel, message=f'<b>❌ Не удалось разгадать каптчу, решите ее сами.</b>', parse_mode='HTML') 
                print(f'[!] Ошибка антикаптчи > Не удалось разгадать каптчу, решите ее сами.')
                captches.append(recognized_text)
    print(f'[$] Антикаптча подключена!')

async def main():
    global client
    try:
        client = await create_client()
        
        # Проверка авторизации
        me = await client.get_me()
        print(f"Авторизован как: {me.phone}")
        
        # Подключение к каналу
        try:
            await client(JoinChannelRequest('lovec_checkov'))
        except:
            pass

        # Запуск автовывода
        if avto_vivod and avto_vivod_tag:
            asyncio.create_task(pay_out())
            print(f"💰 Автовывод на тег: {avto_vivod_tag}")

        print("🟢 Бот запущен и работает")
        await client.run_until_disconnected()

    except SessionPasswordNeededError:
        print("🔐 Требуется пароль 2FA! Удалите файл сессии и перезапустите.")
    except Exception as e:
        print(f"🔴 Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())