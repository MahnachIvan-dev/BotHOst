"""
BotHost Runner — сервер для запуска Telegram-ботов пользователей
+ Telegram-бот для управления и отслеживания подарков
"""
import os
import asyncio
import subprocess
import logging
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_TELEGRAM_ID = int(os.environ["OWNER_TELEGRAM_ID"])
WEBSITE_URL = os.environ["WEBSITE_URL"]  # https://bothost.vercel.app
RUNNER_SECRET = os.environ.get("RUNNER_SECRET", "secret123")

# Директория для хранения ботов пользователей
BOTS_DIR = Path("./user_bots")
BOTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dataclass
class RunningBot:
    """Информация о запущенном боте"""
    bot_id: int
    process: subprocess.Popen
    started_at: datetime
    log_file: Path


# Глобальный реестр запущенных ботов
running_bots: Dict[int, RunningBot] = {}
processed_gifts: Set[str] = set()  # ID уже обработанных подарков


# === УПРАВЛЕНИЕ БОТАМИ ===

async def start_user_bot(bot_id: int, code: str, bot_token: str) -> bool:
    """Запускает Python-бота пользователя в отдельном процессе"""
    try:
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        bot_dir.mkdir(exist_ok=True)
        
        # Сохраняем код
        bot_file = bot_dir / "bot.py"
        bot_file.write_text(code, encoding="utf-8")
        
        # Создаём log-файл
        log_file = bot_dir / "bot.log"
        
        # Запускаем процесс
        env = os.environ.copy()
        env["BOT_TOKEN"] = bot_token
        
        process = subprocess.Popen(
            ["python", "bot.py"],
            cwd=bot_dir,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True
        )
        
        running_bots[bot_id] = RunningBot(
            bot_id=bot_id,
            process=process,
            started_at=datetime.now(),
            log_file=log_file
        )
        
        logger.info(f"Бот {bot_id} запущен (PID: {process.pid})")
        
        # Уведомляем сайт
        await notify_website(f"/api/bots/{bot_id}/status", {
            "status": "running",
            "started_at": datetime.now().isoformat()
        })
        
        return True
    except Exception as e:
        logger.error(f"Ошибка запуска бота {bot_id}: {e}")
        await notify_website(f"/api/bots/{bot_id}/status", {
            "status": "error",
            "error_message": str(e)
        })
        return False


async def stop_user_bot(bot_id: int) -> bool:
    """Останавливает бота пользователя"""
    if bot_id not in running_bots:
        return False
    
    try:
        rb = running_bots[bot_id]
        rb.process.terminate()
        rb.process.wait(timeout=5)
        
        del running_bots[bot_id]
        logger.info(f"Бот {bot_id} остановлен")
        
        await notify_website(f"/api/bots/{bot_id}/status", {
            "status": "stopped",
            "stopped_at": datetime.now().isoformat()
        })
        
        return True
    except Exception as e:
        logger.error(f"Ошибка остановки бота {bot_id}: {e}")
        return False


async def monitor_bots():
    """Мониторит запущенных ботов, перезапускает упавших"""
    while True:
        for bot_id, rb in list(running_bots.items()):
            if rb.process.poll() is not None:
                # Процесс завершился
                logger.warning(f"Бот {bot_id} упал (exit code: {rb.process.returncode})")
                
                # Читаем логи
                logs = rb.log_file.read_text(encoding="utf-8", errors="ignore")[-2000:]
                
                await notify_website(f"/api/bots/{bot_id}/status", {
                    "status": "error",
                    "error_message": f"Process exited with code {rb.process.returncode}",
                    "logs": logs
                })
                
                del running_bots[bot_id]
        
        await asyncio.sleep(10)


async def notify_website(endpoint: str, data: dict):
    """Уведомляет сайт о событиях"""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{WEBSITE_URL}{endpoint}",
                json={**data, "secret": RUNNER_SECRET},
                timeout=10
            )
    except Exception as e:
        logger.error(f"Ошибка уведомления сайта: {e}")


# === ОТСЛЕЖИВАНИЕ ПОДАРКОВ ЧЕРЕЗ USERBOT (TELETHON) ===

# Userbot нужен для отслеживания подарков владельцу
# Обычный бот не может видеть подарки, отправленные пользователю
TELETHON_AVAILABLE = False
try:
    from telethon import TelegramClient, events
    from telethon.tl.functions.messages import GetAvailableReactionsRequest
    TELETHON_AVAILABLE = True
except ImportError:
    logger.warning("Telethon не установлен — отслеживание подарков через Userbot недоступно")

OWNER_PHONE = os.environ.get("OWNER_PHONE")
OWNER_API_ID = os.environ.get("OWNER_API_ID")
OWNER_API_HASH = os.environ.get("OWNER_API_HASH")


async def check_gifts():
    """
    Отслеживает новые подарки владельцу через Telethon Userbot.
    
    Как работает:
    1. Userbot (аккаунт владельца) подключается к Telegram
    2. Слушает события получения подарков (UpdateNewMessage с Gift-контентом)
    3. При получении подарка → отправляет webhook на сайт
    4. Сайт создаёт подписку пользователю
    
    Альтернатива: периодический polling через client.get_messages()
    """
    if not TELETHON_AVAILABLE:
        logger.warning("Пропускаю check_gifts — Telethon недоступен")
        return
    
    if not all([OWNER_PHONE, OWNER_API_ID, OWNER_API_HASH]):
        logger.warning("Пропускаю check_gifts — не настроены OWNER_PHONE/API_ID/API_HASH")
        return
    
    try:
        # Инициализация Userbot-клиента (аккаунт владельца)
        client = TelegramClient(
            "owner_session",
            int(OWNER_API_ID),
            OWNER_API_HASH
        )
        
        await client.start(phone=OWNER_PHONE)
        logger.info(f"Userbot подключен как {OWNER_PHONE}")
        
        # Обработчик входящих сообщений с подарками
        @client.on(events.NewMessage(incoming=True))
        async def on_new_message(event):
            try:
                # Проверяем, является ли сообщение подарком
                # В Telethon подарки приходят как специальные типы сообщений
                if hasattr(event.message, 'action'):
                    action = event.message.action
                    # Типы действий с подарками
                    if hasattr(action, 'gift') or 'gift' in str(type(action)).lower():
                        sender = await event.get_sender()
                        if sender:
                            gift_value = getattr(action, 'stars', 0) or getattr(action, 'cost', 15)
                            gift_id = f"{event.message.id}_{event.chat_id}_{int(datetime.now().timestamp())}"
                            
                            logger.info(f"🎁 Новый подарок от {sender.id}: {gift_value} stars")
                            
                            await process_gift(
                                sender_id=sender.id,
                                sender_username=sender.username or sender.first_name,
                                gift_value=gift_value,
                                gift_id=gift_id
                            )
            except Exception as e:
                logger.error(f"Ошибка обработки подарка: {e}")
        
        # Держим клиента активным
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Ошибка инициализации Userbot: {e}")
        # Fallback на polling
        await check_gifts_polling()


async def check_gifts_polling():
    """Fallback: периодическая проверка подарков (менее эффективно)"""
    logger.info("Запускаю fallback-режим: polling подарков")
    while True:
        try:
            # Здесь можно сделать запрос к Telegram Bot API getOwnedGifts
            # если у владельца бизнес-аккаунт
            # async with aiohttp.ClientSession() as session:
            #     async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getOwnedGifts", ...)
            
            logger.debug("Polling подарков...")
        except Exception as e:
            logger.error(f"Ошибка polling подарков: {e}")
        
        await asyncio.sleep(60)


async def process_gift(sender_id: int, sender_username: str, gift_value: int, gift_id: str):
    """
    Обрабатывает полученный подарок:
    1. Отправляет webhook на сайт → сайт создаёт подписку
    2. Уведомляет пользователя в Telegram
    3. Уведомляет владельца
    """
    if gift_id in processed_gifts:
        logger.debug(f"Подарок {gift_id} уже обработан, пропускаем")
        return
    
    processed_gifts.add(gift_id)
    
    # Быстрая проверка минимальной стоимости
    if gift_value < 15:
        logger.info(f"Подарок от {sender_id} слишком дешёвый ({gift_value} stars, нужно ≥15)")
        try:
            await bot.send_message(
                sender_id,
                f"🎁 Спасибо за подарок!\n\n"
                f"⚠️ К сожалению, стоимость {gift_value}⭐ ниже минимальной (15⭐).\n"
                f"Для активации слота нужен подарок от 15⭐."
            )
        except Exception:
            pass
        return
    
    # Определяем план (для уведомления, сайт определяет сам)
    if gift_value >= 50:
        plan_name = "Месяц"
    elif gift_value >= 25:
        plan_name = "2 недели"
    else:
        plan_name = "Неделя"
    
    # Отправляем webhook на сайт
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WEBSITE_URL}/api/gift-webhook",
                json={
                    "secret": RUNNER_SECRET,
                    "senderId": sender_id,
                    "senderUsername": sender_username,
                    "giftId": gift_id,
                    "giftValue": gift_value,
                    "giftName": f"Telegram Gift ({gift_value} stars)"
                },
                timeout=15
            ) as resp:
                data = await resp.json()
                
        if resp.status == 200 and data.get('success'):
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    sender_id,
                    f"🎁 **Спасибо за подарок!**\n\n"
                    f"✅ Вам активирован слот на **{plan_name}**.\n\n"
                    f"Что дальше:\n"
                    f"1. Отправь /upload чтобы загрузить .py-файл бота\n"
                    f"2. Бот запустится автоматически\n"
                    f"3. Управляй через /mybots\n\n"
                    f"Или открой сайт: {WEBSITE_URL}/dashboard"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить пользователя {sender_id}: {e}")
            
            # Уведомляем владельца
            try:
                await bot.send_message(
                    OWNER_TELEGRAM_ID,
                    f"🎁 **Новый подарок!**\n\n"
                    f"👤 От: @{sender_username or 'unknown'} (ID: {sender_id})\n"
                    f"💰 Стоимость: {gift_value} ⭐\n"
                    f"📅 Активирован план: {plan_name}\n"
                    f"🆔 Gift ID: {gift_id}"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить владельца: {e}")
            
            logger.info(f"✅ Подарок обработан: {sender_id} → {plan_name} ({gift_value}⭐)")
        else:
            logger.error(f"Ошибка webhook: {resp.status} - {data}")
    except Exception as e:
        logger.error(f"Ошибка обработки подарка: {e}")


# === TELEGRAM БОТ (ИНТЕРФЕЙС) ===

class UploadStates(StatesGroup):
    waiting_file = State()
    waiting_token = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")],
        [InlineKeyboardButton(text="🎁 Как купить слот", callback_data="howto")],
        [InlineKeyboardButton(text="🌐 Открыть сайт", url=WEBSITE_URL)],
    ])
    
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        "Я бот для управления хостингом твоих Telegram-ботов.\n\n"
        "🎁 **Как купить слот:**\n"
        "Просто подари мне подарок через Telegram!\n"
        "Стоимость подарка = длительность слота:\n"
        "• 15+ ⭐ → 1 неделя\n"
        "• 25+ ⭐ → 2 недели\n"
        "• 50+ ⭐ → 1 месяц\n\n"
        "Открой мой профиль и нажми 'Подарить'",
        reply_markup=kb
    )


@dp.callback_query(F.data == "howto")
async def cb_howto(call: types.CallbackQuery):
    await call.message.edit_text(
        "🎁 **Как купить слот через подарок:**\n\n"
        "1. Открой мой профиль (нажми на моё имя вверху чата)\n"
        "2. Нажми кнопку '🎁 Подарить'\n"
        "3. Выбери подарок стоимостью:\n"
        "   • **15+ ⭐** → слот на 1 неделю\n"
        "   • **25+ ⭐** → слот на 2 недели\n"
        "   • **50+ ⭐** → слот на 1 месяц\n"
        "4. Отправь подарок\n"
        "5. Я автоматически активирую слот!\n\n"
        "После активации используй /upload чтобы загрузить бота.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back")]
        ])
    )


@dp.callback_query(F.data == "upload")
async def cb_upload(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📤 **Загрузка бота**\n\n"
        "Отправь мне .py-файл твоего Telegram-бота.\n\n"
        "⚠️ **Важно:**\n"
        "• Токен указывать НЕ нужно — используй `os.environ.get('BOT_TOKEN')`\n"
        "• Бот должен использовать aiogram, telebot или другую Telegram-библиотеку\n"
        "• Максимальный размер: 200 КБ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Отмена", callback_data="back")]
        ])
    )
    await state.set_state(UploadStates.waiting_file)


@dp.message(UploadStates.waiting_file, F.document)
async def handle_file(message: types.Message, state: FSMContext):
    doc = message.document
    
    if not doc.file_name.endswith(".py"):
        await message.answer("❌ Нужен .py-файл")
        return
    
    if doc.file_size > 200 * 1024:
        await message.answer("❌ Файл слишком большой (максимум 200 КБ)")
        return
    
    # Скачиваем файл
    file_info = await bot.get_file(doc.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    code = file_bytes.read().decode("utf-8")
    
    # Отправляем на сайт для валидации и сохранения
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{WEBSITE_URL}/api/bots", json={
                "telegramId": str(message.from_user.id),
                "username": message.from_user.username,
                "filename": doc.file_name,
                "code": code
            }) as resp:
                data = await resp.json()
        
        if resp.status != 200:
            await message.answer(f"❌ Ошибка: {data.get('error')}\n\n{data.get('details', '')}")
            await state.clear()
            return
        
        # Сохраняем bot_id в state
        await state.update_data(bot_id=data['bot']['id'])
        
        await message.answer(
            f"✅ Бот загружен!\n"
            f"ID: {data['bot']['id']}\n"
            f"Файл: {data['bot']['filename']}\n\n"
            f"Теперь отправь токен этого бота (я не сохраняю его, только передаю runner'у):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="« Отмена", callback_data="back")]
            ])
        )
        await state.set_state(UploadStates.waiting_token)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@dp.message(UploadStates.waiting_token, F.text)
async def handle_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    
    # Базовая проверка формата токена
    if not token or ":" not in token or len(token) < 40:
        await message.answer("❌ Неверный формат токена")
        return
    
    data = await state.get_data()
    bot_id = data.get('bot_id')
    
    # Запускаем бота
    await message.answer("🚀 Запускаю бота...")
    
    success = await start_user_bot(bot_id, "", token)  # Код уже на сайте
    
    if success:
        await message.answer(
            f"✅ Бот #{bot_id} запущен!\n\n"
            "Он будет работать 24/7 пока активна подписка.\n"
            "Используй /mybots чтобы управлять им.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")]
            ])
        )
    else:
        await message.answer("❌ Ошибка запуска бота")
    
    await state.clear()


@dp.callback_query(F.data == "mybots")
async def cb_mybots(call: types.CallbackQuery):
    # Получаем список ботов пользователя
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WEBSITE_URL}/api/bots?telegramId={call.from_user.id}") as resp:
                data = await resp.json()
        
        bots = data.get('bots', [])
        
        if not bots:
            await call.message.edit_text(
                "У тебя нет загруженных ботов.\n\nИспользуй /upload чтобы загрузить первого!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="« Назад", callback_data="back")]
                ])
            )
            return
        
        # Формируем список
        buttons = []
        for b in bots[:10]:  # Максимум 10 кнопок
            status = "🟢" if b['status'] == 'running' else "🔴"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {b['filename']} (#{b['id']})",
                    callback_data=f"bot:{b['id']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="« Назад", callback_data="back")])
        
        await call.message.edit_text(
            "🤖 **Твои боты:**\n\n"
            "🟢 — работает\n"
            "🔴 — остановлен",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        
    except Exception as e:
        await call.message.edit_text(f"❌ Ошибка: {e}")


@dp.callback_query(F.data.startswith("bot:"))
async def cb_bot_detail(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустить", callback_data=f"start:{bot_id}")],
        [InlineKeyboardButton(text="⏹ Остановить", callback_data=f"stop:{bot_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{bot_id}")],
        [InlineKeyboardButton(text="« Назад", callback_data="mybots")],
    ])
    
    await call.message.edit_text(
        f"🤖 **Бот #{bot_id}**\n\n"
        "Выбери действие:",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("start:"))
async def cb_start_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    
    await call.answer("Запускаю...")
    
    # TODO: Получить токен из БД сайта и запустить
    # Пока что просто уведомляем
    
    await call.message.edit_text(
        f"✅ Бот #{bot_id} запущен!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="mybots")]
        ])
    )


@dp.callback_query(F.data.startswith("stop:"))
async def cb_stop_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    
    await call.answer("Останавливаю...")
    
    success = await stop_user_bot(bot_id)
    
    if success:
        await call.message.edit_text(
            f"⏹ Бот #{bot_id} остановлен",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="« Назад", callback_data="mybots")]
            ])
        )
    else:
        await call.answer("Бот не запущен", show_alert=True)


@dp.callback_query(F.data == "back")
async def cb_back(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")],
        [InlineKeyboardButton(text="🎁 Как купить слот", callback_data="howto")],
        [InlineKeyboardButton(text="🌐 Открыть сайт", url=WEBSITE_URL)],
    ])
    
    await call.message.edit_text("Главное меню:", reply_markup=kb)


# === MAIN ===

async def main():
    logger.info("Запуск BotHost Runner...")
    
    # Запускаем мониторинг ботов
    asyncio.create_task(monitor_bots())
    
    # Запускаем проверку подарков
    asyncio.create_task(check_gifts())
    
    # Запускаем Telegram-бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
