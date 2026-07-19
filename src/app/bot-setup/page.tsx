'use client';

import { useState } from 'react';

export default function BotSetupPage() {
  const [copied, setCopied] = useState('');

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(''), 1500);
  };

  const botCode = `"""
BotHost — Telegram-бот для управления хостингом
Это ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ (не сайт!)
Запускается на runner-сервере (Railway)

ОПЛАТА: только через Telegram Stars (XTR)
Звёзды идут напрямую владельцу бота
"""
import os
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, ContentType
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBSITE_URL = os.environ["WEBSITE_URL"]  # https://bothost.vercel.app
OWNER_ID = int(os.environ["OWNER_TELEGRAM_ID"])
PROVIDER_TOKEN = ""  # ПУСТОЙ для Telegram Stars!

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)


class UploadStates(StatesGroup):
    waiting_file = State()


# === ГЛАВНОЕ МЕНЮ ===
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")],
        [InlineKeyboardButton(text="💎 Купить слот", callback_data="pricing")],
        [InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="🌐 Открыть сайт", url=WEBSITE_URL)],
        [InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin")],
    ])


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\\n\\n"
        "Я бот для управления хостингом твоих Telegram-ботов.\\n\\n"
        "📤 Загружай .py-файлы прямо здесь\\n"
        "⭐ Оплачивай слоты через Telegram Stars\\n"
        "🎁 Активируй промокоды на бесплатные слоты",
        reply_markup=main_kb()
    )


# === ЗАГРУЗКА ФАЙЛА ===
@dp.callback_query(F.data == "upload")
async def cb_upload(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(
        "📤 Отправь мне .py-файл твоего Telegram-бота.\\n\\n"
        "⚠️ Токен в коде указывать НЕ нужно — используй:\\n"
        "\`os.environ.get('BOT_TOKEN')\`"
    )
    await state.set_state(UploadStates.waiting_file)


@dp.message(UploadStates.waiting_file, F.document)
async def handle_file(message: types.Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.endswith(".py"):
        return await message.answer("❌ Нужен .py-файл")

    file_info = await bot.get_file(doc.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    code = file_bytes.read().decode("utf-8")

    async with aiohttp.ClientSession() as s:
        async with s.post(f"{WEBSITE_URL}/api/bots", json={
            "telegramId": str(message.from_user.id),
            "username": message.from_user.username,
            "filename": doc.file_name,
            "code": code,
        }) as r:
            data = await r.json()

    if r.status != 200:
        await message.answer(f"❌ Ошибка: {data.get('error')}")
    else:
        await message.answer(
            f"✅ Бот загружен!\\n"
            f"ID: {data['bot']['id']}\\n"
            f"Файл: {data['bot']['filename']}\\n\\n"
            "Открой сайт, чтобы запустить →",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 К моим ботам", url=f"{WEBSITE_URL}/dashboard")]
            ])
        )
    await state.clear()


# === ПОКУПКА ===
@dp.callback_query(F.data == "pricing")
async def cb_pricing(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Неделя — 15⭐", callback_data="buy:week")],
        [InlineKeyboardButton(text="📅 2 недели — 25⭐", callback_data="buy:2weeks")],
        [InlineKeyboardButton(text="📅 Месяц — 50⭐", callback_data="buy:month")],
        [InlineKeyboardButton(text="« Назад", callback_data="back")],
    ])
    await call.message.edit_text(
        "💎 Выберите тариф:\\n\\n"
        "Оплата через Telegram Stars.\\n"
        "Звёзды пойдут напрямую владельцу.",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: types.CallbackQuery):
    plan = call.data.split(":")[1]
    plans = {
        "week": ("Неделя", 15),
        "2weeks": ("2 недели", 25),
        "month": ("Месяц", 50),
    }
    title, stars = plans[plan]

    await call.message.answer_invoice(
        title=f"Слот на {title}",
        description="1 слот для Telegram-бота",
        payload=f"slot_{plan}_{call.from_user.id}",
        provider_token=PROVIDER_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label=f"Слот {title}", amount=stars)],
    )


@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def on_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    plan = payload.split("_")[1]
    days = {"week": 7, "2weeks": 14, "month": 30}[plan]

    async with aiohttp.ClientSession() as s:
        async with s.post(f"{WEBSITE_URL}/api/subscriptions", json={
            "telegramId": str(message.from_user.id),
            "username": message.from_user.username,
            "planId": plan,
            "confirmed": True,
        }) as r:
            await r.json()

    # Уведомление владельцу
    await bot.send_message(
        OWNER_ID,
        f"💰 Оплата от {message.from_user.full_name} (@{message.from_user.username})\\n"
        f"План: {plan}, звёзд: {message.successful_payment.total_amount}"
    )

    await message.answer(
        f"✅ Оплата прошла! Слот активирован на {days} дней.",
        reply_markup=main_kb()
    )


# === ПРОМОКОДЫ ===
@dp.callback_query(F.data == "promo")
async def cb_promo(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("🎁 Введите промокод:")
    await state.set_state("promo_input")


@dp.message(F.text, F.state("promo_input"))
async def handle_promo(message: types.Message, state: FSMContext):
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{WEBSITE_URL}/api/promo", json={
            "telegramId": str(message.from_user.id),
            "username": message.from_user.username,
            "code": message.text.strip(),
        }) as r:
            data = await r.json()

    if r.status == 200:
        await message.answer(f"🎉 {data['message']}")
    else:
        await message.answer(f"❌ {data.get('error')}")
    await state.clear()


# === АДМИН-ПАНЕЛЬ (в боте) ===
@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return await call.answer("У вас нет прав", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin:users")],
        [InlineKeyboardButton(text="🤖 Все боты", callback_data="admin:bots")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="🌐 Открыть веб-админку", url=f"{WEBSITE_URL}/admin")],
        [InlineKeyboardButton(text="« Назад", callback_data="back")],
    ])
    await call.message.edit_text("🔐 Админ-панель:", reply_markup=kb)


@dp.callback_query(F.data == "admin:stats")
async def admin_stats(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{WEBSITE_URL}/api/admin?section=stats&adminId={OWNER_ID}") as r:
            data = await r.json()
    s = data.get("stats", {})
    await call.message.edit_text(
        f"📊 Статистика:\\n\\n"
        f"👥 Пользователей: {s.get('totalUsers', 0)}\\n"
        f"🤖 Всего ботов: {s.get('totalBots', 0)}\\n"
        f"▶️ Работает: {s.get('runningBots', 0)}\\n"
        f"💳 Подписок: {s.get('activeSubscriptions', 0)}\\n"
        f"⭐ Звёзд: {s.get('totalRevenue', 0)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="admin")]
        ])
    )


@dp.callback_query(F.data == "back")
async def cb_back(call: types.CallbackQuery):
    await call.message.edit_text(
        "Главное меню:",
        reply_markup=main_kb()
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
`;

  const requirements = `aiogram>=3.0
aiohttp
python-dotenv`;

  const envExample = `BOT_TOKEN=1234567890:ABCdefGhI...
WEBSITE_URL=https://bothost.vercel.app
OWNER_TELEGRAM_ID=123456789`;

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        🤖 Telegram-бот для хостинга
      </h1>
      <p className="text-slate-400 mb-4">
        Полный код Python-бота для управления хостингом + runner-сервер для запуска ботов пользователей.
      </p>

      <div className="mb-8 bg-gradient-to-r from-pink-900/30 to-purple-900/30 border border-pink-500/30 rounded-xl p-6">
        <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
          🎁 Новая система оплаты через Telegram Gifts
        </h3>
        <p className="text-slate-300 text-sm mb-3">
          Пользователи <strong>дарят подарки владельцу бота</strong> через Telegram. 
          Runner-сервер отслеживает полученные подарки через Userbot API и <strong>автоматически активирует слот</strong>:
        </p>
        <ul className="space-y-1 text-sm text-slate-300">
          <li>🎁 Подарок <strong>15+ ⭐</strong> → слот на <strong>1 неделю</strong></li>
          <li>🎁 Подарок <strong>25+ ⭐</strong> → слот на <strong>2 недели</strong></li>
          <li>🎁 Подарок <strong>50+ ⭐</strong> → слот на <strong>1 месяц</strong></li>
        </ul>
        <p className="text-slate-400 text-xs mt-3">
          Владелец получает подарки напрямую, без комиссий платформ.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <a
          href="https://t.me/YourBotHostBot"
          target="_blank"
          className="block bg-gradient-to-br from-blue-600 to-cyan-500 rounded-2xl p-6 hover:scale-[1.02] transition-transform shadow-xl shadow-blue-500/30"
        >
          <div className="text-5xl mb-3">📱</div>
          <h3 className="text-2xl font-bold mb-1">Открыть бота</h3>
          <p className="text-blue-100 text-sm">@YourBotHostBot в Telegram</p>
        </a>
        <a
          href="/dashboard"
          className="block bg-gradient-to-br from-purple-600 to-pink-500 rounded-2xl p-6 hover:scale-[1.02] transition-transform shadow-xl shadow-purple-500/30"
        >
          <div className="text-5xl mb-3">🌐</div>
          <h3 className="text-2xl font-bold mb-1">Личный кабинет</h3>
          <p className="text-purple-100 text-sm">Управляйте ботами на сайте</p>
        </a>
      </div>

      {/* Возможности */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4">Возможности бота</h2>
        <div className="grid md:grid-cols-2 gap-3">
          {[
            ['📤', 'Загрузка .py файлов ботов прямо в чат'],
            ['⭐', 'Оплата через Telegram Stars (XTR)'],
            ['🎁', 'Активация промокодов'],
            ['🤖', 'Список ваших ботов и управление'],
            ['🔐', 'Встроенная админ-панель для владельца'],
            ['🔗', 'Ссылка на веб-кабинет'],
          ].map(([icon, text]) => (
            <div key={text} className="bg-slate-900/40 border border-blue-900/40 rounded-lg p-3 flex items-center gap-3">
              <span className="text-2xl">{icon}</span>
              <span className="text-slate-300 text-sm">{text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Код бота */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-2xl font-bold">📄 bot.py</h2>
          <button
            onClick={() => copy(botCode, 'bot')}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            {copied === 'bot' ? '✓ Скопировано' : '📋 Копировать'}
          </button>
        </div>
        <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-xs overflow-x-auto max-h-[500px] overflow-y-auto">
          <code>{botCode}</code>
        </pre>
      </section>

      <section className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-2xl font-bold">📦 requirements.txt</h2>
          <button
            onClick={() => copy(requirements, 'req')}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            {copied === 'req' ? '✓ Скопировано' : '📋 Копировать'}
          </button>
        </div>
        <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-sm font-mono">
          {requirements}
        </pre>
      </section>

      <section className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-2xl font-bold">⚙️ .env (для runner-сервера)</h2>
          <button
            onClick={() => copy(envExample, 'env')}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            {copied === 'env' ? '✓ Скопировано' : '📋 Копировать'}
          </button>
        </div>
        <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-sm font-mono">
          {envExample}
        </pre>
      </section>

      {/* Запуск */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4">🚀 Как запустить</h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <ol className="list-decimal ml-5 space-y-2 text-slate-300">
            <li>Создайте бота через <a href="https://t.me/BotFather" target="_blank" className="text-blue-400">@BotFather</a>, получите токен</li>
            <li>Узнайте свой Telegram ID через <a href="https://t.me/userinfobot" target="_blank" className="text-blue-400">@userinfobot</a></li>
            <li>Установите зависимости: <code className="bg-slate-950 px-2 rounded">pip install -r requirements.txt</code></li>
            <li>Заполните <code className="bg-slate-950 px-2 rounded">.env</code> файл</li>
            <li>Запустите: <code className="bg-slate-950 px-2 rounded">python bot.py</code></li>
            <li>Разместите на <strong>Railway / Render / VPS</strong> для 24/7 работы</li>
          </ol>
        </div>
      </section>

      <div className="bg-gradient-to-r from-blue-900/40 to-cyan-900/40 border border-blue-500/30 rounded-xl p-6">
        <h3 className="text-xl font-bold mb-2">💡 Как работают платежи Stars</h3>
        <p className="text-slate-300 text-sm mb-2">
          Telegram Stars — внутренняя валюта Telegram. При оплате через <code className="bg-slate-950 px-1 rounded">sendInvoice</code> с пустым <code className="bg-slate-950 px-1 rounded">provider_token</code> и валютой <code className="bg-slate-950 px-1 rounded">XTR</code> звёзды автоматически поступают <strong>владельцу бота</strong>.
        </p>
        <p className="text-slate-300 text-sm">
          Вывести звёзды можно через <a href="https://t.me/BotFather" target="_blank" className="text-blue-400">@BotFather</a> → Bot Settings → Payments → Telegram Stars Balance.
        </p>
      </div>
    </div>
  );
}
