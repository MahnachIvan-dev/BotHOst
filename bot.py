"""
🤖 BotHost — хостинг Telegram-ботов (Версия 4.2 — Cloud Backup)
✅ Сохранение и восстановление базы через Telegram!
✅ Система ПРОМОКОДОВ
✅ Поддержка .zip архивов
✅ Лимит 20 МБ
✅ Ручное подтверждение оплат
"""

import os
import re
import sys
import asyncio
import subprocess
import sqlite3
import logging
import signal
import html
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ═══════════════════════════════════════════════════════════════
# 🔧 КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8711311188:AAHnhjvLhyYASMxUI-1hLyktHXhSsmYXnww")
OWNER_ID = 8269807543  # Твой ID
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "ivan_unreal")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
BOTS_DIR = DATA_DIR / "bots"
DB_PATH = DATA_DIR / "bot.db"
WELCOME_IMAGE = DATA_DIR / "welcome.jpg"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BOTS_DIR.mkdir(parents=True, exist_ok=True)

PLANS = {
    "week":   {"name": "Неделя",    "stars": 15, "days": 7,  "emoji": "📅"},
    "2weeks": {"name": "2 недели",  "stars": 25, "days": 14, "emoji": "📅"},
    "month":  {"name": "Месяц",     "stars": 50, "days": 30, "emoji": "🗓"},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-7s │ %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("BotHost")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
running_bots: Dict[int, subprocess.Popen] = {}

# ═══════════════════════════════════════════════════════════════
# 💾 БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT, expires_at TEXT, created_at TEXT, gift_id TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT, bot_token TEXT, status TEXT DEFAULT 'stopped', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS payment_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, plan TEXT, status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, plan TEXT, uses_left INTEGER, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, promo_id INTEGER, UNIQUE(user_id, promo_id))""")
    conn.commit()
    conn.close()

def get_db(): return sqlite3.connect(DB_PATH)

def create_user(user_id, username, full_name=""):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username = ?, full_name = ?", (user_id, username, full_name, datetime.now().isoformat(), username, full_name))
    conn.commit(); conn.close()

def get_all_users():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall(); conn.close()
    return rows

def is_user_banned(user_id):
    if user_id == OWNER_ID: return False
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone(); conn.close()
    return bool(row and row[0])

def ban_user(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def unban_user(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def is_admin(user_id):
    if user_id == OWNER_ID: return True
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone(); conn.close()
    return bool(row and row[0])

def add_admin(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)", (user_id, datetime.now().isoformat()))
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def remove_admin(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def get_all_admins():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 1 AND user_id != ?", (OWNER_ID,))
    rows = c.fetchall(); conn.close()
    return rows

def has_active_slot(user_id):
    if user_id == OWNER_ID or is_admin(user_id): return True
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM slots WHERE user_id = ? AND expires_at > ?", (user_id, datetime.now().isoformat()))
    count = c.fetchone()[0]; conn.close()
    return count > 0

def get_active_slots(user_id):
    if user_id == OWNER_ID: return [(0, OWNER_ID, "owner", "2099-12-31", datetime.now().isoformat(), "owner")]
    if is_admin(user_id): return [(0, user_id, "admin", "2099-12-31", datetime.now().isoformat(), "admin")]
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM slots WHERE user_id = ? AND expires_at > ?", (user_id, datetime.now().isoformat()))
    rows = c.fetchall(); conn.close()
    return rows

def create_slot(user_id, plan):
    days = PLANS[plan]["days"]
    expires_at = datetime.now() + timedelta(days=days)
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO slots (user_id, plan, expires_at, created_at) VALUES (?, ?, ?, ?)", (user_id, plan, expires_at.isoformat(), datetime.now().isoformat()))
    conn.commit(); conn.close()

def save_bot(user_id, filename, user_bot_token):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO bots (user_id, filename, bot_token, created_at) VALUES (?, ?, ?, ?)", (user_id, filename, user_bot_token, datetime.now().isoformat()))
    bot_id = c.lastrowid
    conn.commit(); conn.close()
    return bot_id

def get_user_bots(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE user_id = ?", (user_id,))
    rows = c.fetchall(); conn.close()
    return rows

def get_bot(bot_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
    row = c.fetchone(); conn.close()
    return row

def delete_bot_record(bot_id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def get_all_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots")
    rows = c.fetchall(); conn.close()
    return rows

def create_payment_request(user_id: int, username: str, full_name: str, plan: str) -> int:
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO payment_requests (user_id, username, full_name, plan, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, username, full_name, plan, datetime.now().isoformat()))
    req_id = c.lastrowid
    conn.commit(); conn.close()
    return req_id

def get_pending_requests():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM payment_requests WHERE status = 'pending' ORDER BY created_at ASC")
    rows = c.fetchall(); conn.close()
    return rows

def get_payment_request(req_id: int):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
    row = c.fetchone(); conn.close()
    return row

def approve_payment(req_id: int):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'approved', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), req_id))
    conn.commit(); conn.close()

def reject_payment(req_id: int):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'rejected', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), req_id))
    conn.commit(); conn.close()

def user_has_pending_request(user_id: int) -> bool:
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE user_id = ? AND status = 'pending'", (user_id,))
    count = c.fetchone()[0]; conn.close()
    return count > 0

def create_promo(code: str, plan: str, uses: int):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO promocodes (code, plan, uses_left, created_at) VALUES (?, ?, ?, ?)", (code, plan, uses, datetime.now().isoformat()))
        conn.commit(); conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_all_promos():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, code, plan, uses_left FROM promocodes WHERE uses_left > 0")
    rows = c.fetchall(); conn.close()
    return rows

def delete_promo(promo_id: int):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE id = ?", (promo_id,))
    conn.commit(); conn.close()

def use_promo(user_id: int, code: str):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, plan, uses_left FROM promocodes WHERE code = ?", (code,))
    promo = c.fetchone()
    
    if not promo or promo[2] <= 0:
        conn.close()
        return False, "❌ Промокод не найден или закончился."
        
    c.execute("SELECT 1 FROM used_promos WHERE user_id = ? AND promo_id = ?", (user_id, promo[0]))
    if c.fetchone():
        conn.close()
        return False, "⚠️ Ты уже использовал этот промокод."
        
    c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE id = ?", (promo[0],))
    c.execute("INSERT INTO used_promos (user_id, promo_id) VALUES (?, ?)", (user_id, promo[0]))
    conn.commit()
    conn.close()
    
    create_slot(user_id, promo[1])
    return True, promo[1]

def get_stats():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1"); banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1"); admins = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM slots WHERE expires_at > ?", (datetime.now().isoformat(),))
    active_slots = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bots"); total_bots = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"); pending_reqs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE status = 'approved'"); approved_reqs = c.fetchone()[0]
    conn.close()
    return {
        "total_users": total_users, "banned": banned, "admins": admins,
        "active_slots": active_slots, "total_bots": total_bots,
        "running_bots": len(running_bots),
        "pending_reqs": pending_reqs, "approved_reqs": approved_reqs
    }

# ═══════════════════════════════════════════════════════════════
# 🚀 УНИВЕРСАЛЬНЫЙ WRAPPER
# ═══════════════════════════════════════════════════════════════

WRAPPER_CODE = '''#!/usr/bin/env python3
import os, sys, re, signal, subprocess, time, traceback

ENTRY_POINT = "{{ENTRY_POINT}}"

def log(msg): print(f"[BotHost] {msg}", flush=True)
log(f"Запуск проекта. Исполняемый файл: {ENTRY_POINT}")

STDLIB_MODULES = {"os", "sys", "re", "json", "time", "datetime", "asyncio", "logging", "pathlib", "typing", "subprocess", "signal", "html", "math", "random", "collections", "itertools", "functools", "traceback", "threading", "queue", "socket", "urllib", "http", "email", "base64", "hashlib", "hmac", "uuid", "sqlite3", "csv", "io", "tempfile", "shutil", "copy", "argparse", "warnings", "contextlib", "dataclasses", "enum", "abc", "inspect", "operator", "string", "textwrap", "unicodedata", "struct", "codecs", "pickle", "gzip", "zipfile", "tarfile", "glob", "fnmatch", "builtins", "statistics", "secrets", "ssl", "calendar"}
PIP_MAPPING = {"telebot": "pyTelegramBotAPI", "cv2": "opencv-python", "PIL": "Pillow", "yaml": "PyYAML", "bs4": "beautifulsoup4", "dotenv": "python-dotenv", "telegram": "python-telegram-bot", "discord": "discord.py"}

def is_installed(m):
    try: __import__(m); return True
    except: return False

if os.path.exists("requirements.txt"):
    log("Устанавливаем пакеты из requirements.txt...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet", "--no-cache-dir"])
else:
    imports = set()
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and file != "wrapper.py":
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        for line in f.read().split("\\n"):
                            line = line.strip()
                            m = re.match(r"^import\\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                            if m: imports.add(m.group(1))
                            m = re.match(r"^from\\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                            if m: imports.add(m.group(1))
                except: pass
    missing = [imp for imp in imports if imp not in STDLIB_MODULES and not is_installed(imp)]
    if missing:
        log(f"Устанавливаем: {missing}")
        for mod in missing:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir", PIP_MAPPING.get(mod, mod)])

process = None
def handle_signal(signum, frame):
    log("Выключаем бота...")
    if process:
        process.terminate()
        try: process.wait(timeout=5)
        except: process.kill()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

if not os.path.exists(ENTRY_POINT):
    log(f"ОШИБКА: Файл {ENTRY_POINT} не найден!"); sys.exit(1)

log("🚀 Запускаем главный процесс!")
sys.stdout.flush()
process = subprocess.Popen([sys.executable, "-u", ENTRY_POINT], env=os.environ.copy())
while True:
    ret = process.poll()
    if ret is not None: sys.exit(ret)
    time.sleep(1)
'''

async def start_user_bot(bot_id: int) -> bool:
    try:
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        log_file = bot_dir / "bot.log"
        bot_data = get_bot(bot_id)
        user_bot_token = bot_data[3]

        env = os.environ.copy()
        if user_bot_token: env["BOT_TOKEN"] = user_bot_token
        else: env.pop("BOT_TOKEN", None)
        env["PYTHONUNBUFFERED"] = "1"

        with open(log_file, "w", encoding="utf-8") as lf:
            process = subprocess.Popen([sys.executable, "-u", "wrapper.py"], cwd=str(bot_dir), env=env, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)

        running_bots[bot_id] = process
        await asyncio.sleep(8)
        if process.poll() is not None:
            await asyncio.sleep(4)
            if process.poll() is not None:
                conn = get_db(); c = conn.cursor()
                c.execute("UPDATE bots SET status = 'error' WHERE id = ?", (bot_id,))
                conn.commit(); conn.close()
                if bot_id in running_bots: del running_bots[bot_id]
                return False

        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
        conn.commit(); conn.close()
        return True
    except: return False

async def stop_user_bot(bot_id: int):
    if bot_id in running_bots:
        proc = running_bots[bot_id]
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try: proc.wait(timeout=5)
                except: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except: pass
        finally:
            if bot_id in running_bots: del running_bots[bot_id]
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def get_bot_logs(bot_id: int, lines: int = 50) -> str:
    log_file = BOTS_DIR / f"bot_{bot_id}" / "bot.log"
    if not log_file.exists(): return "📭 Логи пустые"
    try:
        content = log_file.read_text(encoding="utf-8", errors="ignore")
        return "\n".join(content.strip().split("\n")[-lines:]) or "📭 Логи пустые"
    except: return "❌ Ошибка чтения логов"

async def monitor_bots():
    while True:
        try:
            for bot_id, proc in list(running_bots.items()):
                if proc.poll() is not None:
                    code = proc.returncode
                    del running_bots[bot_id]
                    conn = get_db(); c = conn.cursor()
                    c.execute("UPDATE bots SET status = 'error' WHERE id = ?", (bot_id,))
                    c.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
                    row = c.fetchone(); conn.commit(); conn.close()

                    if row and row[0] != OWNER_ID:
                        logs = get_bot_logs(bot_id, 10)
                        try: await bot.send_message(row[0], f"⚠️ <b>Бот #{bot_id} упал</b>\nКод: {code}\n<pre>{html.escape(logs[-500:])}</pre>", parse_mode="HTML")
                        except: pass
                else:
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
                    row = c.fetchone(); conn.close()
                    if row:
                        uid = row[0]
                        if uid != OWNER_ID and not is_admin(uid):
                            if is_user_banned(uid) or not has_active_slot(uid):
                                await stop_user_bot(bot_id)
        except: pass
        await asyncio.sleep(30)

async def restore_running_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, user_id FROM bots WHERE status = 'running'")
    bots_to_restore = c.fetchall(); conn.close()
    for bot_id, user_id in bots_to_restore:
        if is_user_banned(user_id): continue
        if user_id != OWNER_ID and not is_admin(user_id) and not has_active_slot(user_id): continue
        await start_user_bot(bot_id)

async def auto_backup():
    """Отправляет базу данных владельцу каждые 24 часа"""
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            if os.path.exists(DB_PATH):
                await bot.send_document(OWNER_ID, FSInputFile(DB_PATH, filename=f"bothost_backup_{datetime.now().strftime('%Y%m%d')}.db"), caption="🔄 Ежедневный авто-бэкап базы данных")
        except: pass

# ═══════════════════════════════════════════════════════════════
# 💬 ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════════

def get_profile_link():
    return f"https://t.me/{OWNER_USERNAME}" if OWNER_USERNAME else f"tg://user?id={OWNER_ID}"

WELCOME_TEXT = """👋 <b>Привет, {name}!</b>

Я — <b>BotHost</b>, профессиональный хостинг для Telegram-ботов.

━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>Особенности:</b>
• Поддержка загрузки <b>.zip архивов</b>
• Лимит до <b>20 МБ</b>
• Авто-чтение <code>requirements.txt</code>
━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>Как начать?</b>
1️⃣ Купи слот или введи промокод
2️⃣ Нажми «📤 Загрузить бота»
3️⃣ Отправь ZIP-архив с твоим кодом
4️⃣ Запусти бота!"""

def main_menu_kb(user_id):
    buttons = [
        [InlineKeyboardButton(text="💎 Купить слот", callback_data="buy"), InlineKeyboardButton(text="🎟 Промокод", callback_data="promo_enter")],
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots"), InlineKeyboardButton(text="📊 Мои слоты", callback_data="myslots")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ]
    if is_admin(user_id): buttons.append([InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_welcome(target, edit=False):
    user_id = target.from_user.id if hasattr(target, 'from_user') else target.chat.id
    name = target.from_user.first_name if hasattr(target, 'from_user') else "друг"
    text = WELCOME_TEXT.format(name=name)
    kb = main_menu_kb(user_id)
    chat_id = target.chat.id if hasattr(target, 'chat') else user_id

    if edit:
        try: return await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except: pass
    try: await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
    except: pass

# ═══════════════════════════════════════════════════════════════
# 📝 FSM СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════

class UploadStates(StatesGroup):
    waiting_file = State()
    waiting_token = State()

class UserStates(StatesGroup):
    enter_promo = State()

class AdminStates(StatesGroup):
    broadcast = State()
    ban = State()
    unban = State()
    addadmin = State()
    promo_code = State()
    promo_uses = State()

# ═══════════════════════════════════════════════════════════════
# 📱 ХЕНДЛЕРЫ
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if is_user_banned(message.from_user.id): return await message.answer("🚫 <b>Вы заблокированы</b>", parse_mode="HTML")
    create_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await send_welcome(message)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear(); await message.answer("❌ Действие отменено.")

# --- ВОССТАНОВЛЕНИЕ БАЗЫ ДАННЫХ ИЗ ФАЙЛА (.DB) ---
@dp.message(F.document, F.from_user.id == OWNER_ID)
async def admin_db_restore(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    # Если мы не в состоянии загрузки бота, а админ кидает файл базы данных
    if current_state is None and message.document.file_name.endswith(".db"):
        await message.answer("⏳ Скачиваю новую базу данных...")
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=DB_PATH)
        await message.answer("✅ <b>База данных успешно восстановлена!</b>\n\nСделайте рестарт ботов в админ-панели.", parse_mode="HTML")
        return

# ─── FSM: ПРОМОКОДЫ ДЛЯ ЮЗЕРА ─────────────

@dp.callback_query(F.data == "promo_enter")
async def cb_promo_enter(call: types.CallbackQuery, state: FSMContext):
    if is_user_banned(call.from_user.id): return await call.answer("🚫 Заблокированы", show_alert=True)
    await call.message.edit_text("🎟 <b>Ввод промокода</b>\n\nОтправьте мне промокод сообщением:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="back_main")]]), parse_mode="HTML")
    await state.set_state(UserStates.enter_promo)

@dp.message(UserStates.enter_promo)
async def process_promo(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    success, result = use_promo(message.from_user.id, code)
    
    if success:
        plan_info = PLANS[result]
        await message.answer(f"🎉 <b>Промокод активирован!</b>\n\nВы получили тариф: {plan_info['emoji']} <b>{plan_info['name']}</b> ({plan_info['days']} дней).\n\nТеперь вы можете загрузить своего бота!", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")], [InlineKeyboardButton(text="« Главное меню", callback_data="back_main")]]))
    else:
        await message.answer(result, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« В меню", callback_data="back_main")]]))
    await state.clear()

# ─── FSM: УНИВЕРСАЛЬНАЯ ЗАГРУЗКА (.ZIP / .PY) ─────────────

@dp.message(UploadStates.waiting_file, F.document)

# ═══════════════════════════════════════════════════════════════
# 📤 ЗАГРУЗКА ФАЙЛОВ (исправлено: zip + токен + пересылки)
# ═══════════════════════════════════════════════════════════════

@dp.message(F.document)
async def handle_any_document(message: types.Message, state: FSMContext):
    """Ловит ЛЮБОЙ документ в личке — и по кнопке, и просто скинутый файл"""
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    if is_user_banned(user_id):
        return await message.answer("🚫 Вы заблокированы")

    doc = message.document
    if not doc:
        return await message.answer("❌ Не вижу файл. Пришли документ заново (не сжатое фото).")

    filename = (doc.file_name or "bot.zip").strip()
    # нормализуем имя (кириллица, длинное тире и т.д.)
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    # Владелец может восстановить БД файлом .db
    if user_id == OWNER_ID and ext == "db":
        await message.answer("⏳ Восстанавливаю базу...")
        try:
            file = await bot.get_file(doc.file_id)
            await bot.download_file(file.file_path, destination=DB_PATH)
            init_db()
            return await message.answer("✅ База восстановлена!")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: {e}")

    if not has_active_slot(user_id):
        return await message.answer(
            "❌ Нет активного слота.\nСначала купи слот или введи промокод.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить", callback_data="buy")],
                [InlineKeyboardButton(text="🎟 Промокод", callback_data="promo_enter")],
            ]),
            parse_mode="HTML",
        )

    if ext not in ("py", "txt", "zip"):
        return await message.answer(
            f"❌ Формат <code>.{ext or '?'}</code> не поддерживается.\n"
            f"Нужен <b>.py</b> или <b>.zip</b>\n\nФайл: <code>{html.escape(filename)}</code>",
            parse_mode="HTML",
        )

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await message.answer("❌ Максимум 20 МБ")

    await state.update_data(
        file_id=doc.file_id,
        filename=filename,
        ext=ext,
        file_size=doc.file_size or 0,
    )
    await state.set_state(UploadStates.waiting_token)

    await message.answer(
        f"✅ <b>Файл принят!</b>\n\n"
        f"📁 <code>{html.escape(filename)}</code>\n"
        f"📦 {ext.upper()} · {(doc.file_size or 0) / 1024:.1f} КБ\n\n"
        f"Теперь отправь <b>токен</b> от @BotFather\n"
        f"или напиши <code>none</code>, если токен не нужен.\n\n"
        f"🔒 Сообщение с токеном удалю.",
        parse_mode="HTML",
    )


@dp.message(UploadStates.waiting_token, F.text)
async def handle_token(message: types.Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not raw:
        return await message.answer("⚠️ Пришли токен текстом или <code>none</code>", parse_mode="HTML")

    if raw.lower() in ("none", "нет", "no", "-", "skip", "пропустить"):
        token = ""
        token_status = "🚫 Без токена"
    elif ":" in raw and len(raw) >= 25:
        token = raw
        token_status = "🔐 Токен принят"
    else:
        return await message.answer(
            "⚠️ Это не похоже на токен.\n"
            "Формат: <code>123456:AAH...</code>\n"
            "Или напиши <code>none</code>",
            parse_mode="HTML",
        )

    # удаляем токен из чата
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    file_id = data.get("file_id")
    ext = data.get("ext")
    filename = data.get("filename") or "bot.zip"

    if not file_id:
        await state.clear()
        return await message.answer("❌ Файл потерялся. Скинь .zip/.py ещё раз.")

    status_msg = await message.answer("⏳ Сохраняю и распаковываю на сервер...")

    try:
        bot_id = save_bot(message.from_user.id, filename, token)
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        bot_dir.mkdir(parents=True, exist_ok=True)

        # безопасное имя на диске (без кириллицы в пути архива)
        safe_name = f"upload.{ext}"
        download_path = bot_dir / safe_name

        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=download_path)

        entry_point = "user_bot.py"

        if ext == "zip":
            with zipfile.ZipFile(download_path, "r") as zf:
                # защита от zip-slip
                for m in zf.namelist():
                    p = (bot_dir / m).resolve()
                    if not str(p).startswith(str(bot_dir.resolve())):
                        raise RuntimeError("Небезопасный zip-архив")
                zf.extractall(bot_dir)
            try:
                download_path.unlink()
            except Exception:
                pass

            possible = ["main.py", "bot.py", "app.py", "run.py", "user_bot.py"]
            found = None
            for root, _, files in os.walk(bot_dir):
                for name in possible:
                    if name in files:
                        rel = os.path.relpath(os.path.join(root, name), bot_dir)
                        found = rel.replace("\\", "/")
                        break
                if found:
                    break
            if not found:
                for root, _, files in os.walk(bot_dir):
                    for f in files:
                        if f.endswith(".py") and f != "wrapper.py":
                            rel = os.path.relpath(os.path.join(root, f), bot_dir)
                            found = rel.replace("\\", "/")
                            break
                    if found:
                        break
            if not found:
                await state.clear()
                return await status_msg.edit_text("❌ В архиве нет .py файлов!")
            entry_point = found
        else:
            target = bot_dir / "user_bot.py"
            if download_path != target:
                if target.exists():
                    target.unlink()
                download_path.rename(target)
            entry_point = "user_bot.py"

        (bot_dir / "wrapper.py").write_text(
            WRAPPER_CODE.replace("{{ENTRY_POINT}}", entry_point),
            encoding="utf-8",
        )

        await state.clear()
        await status_msg.edit_text(
            f"✅ <b>Бот развёрнут!</b>\n\n"
            f"🆔 ID: <code>{bot_id}</code>\n"
            f"📁 {html.escape(filename)}\n"
            f"▶ Запуск: <code>{html.escape(entry_point)}</code>\n"
            f"{token_status}\n\n"
            f"Открой «🤖 Мои боты» → ▶️ Запуск",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")]
            ]),
        )
    except Exception as e:
        logger.error("upload error: %s", e, exc_info=True)
        await state.clear()
        try:
            await status_msg.edit_text(f"❌ Ошибка загрузки:\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")
        except Exception:
            await message.answer(f"❌ Ошибка загрузки: {e}")


@dp.message(UploadStates.waiting_file)
async def waiting_file_hint(message: types.Message):
    """Если ждали файл, а прислали текст"""
    await message.answer(
        "📎 Сейчас нужно отправить <b>файл</b>:\n"
        "• <code>.py</code>\n• <code>.zip</code>\n\n"
        "Не токен — сначала файл, потом токен.",
        parse_mode="HTML",
    )


@dp.message(UploadStates.waiting_token)
async def waiting_token_not_text(message: types.Message):
    """Если ждали токен, а прислали снова файл/стикер"""
    await message.answer(
        "🔑 Сейчас нужен <b>токен</b> текстом\n"
        "или <code>none</code>.\n\n"
        "Если хочешь другой файл — /cancel и загрузи заново.",
        parse_mode="HTML",
    )

# ─── Callback ─────────────────────────────────────────────

@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try: await call.message.delete()
    except: pass
    await send_welcome(call.message)

@dp.callback_query(F.data == "buy")
async def cb_buy(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.from_user.id == OWNER_ID or is_admin(call.from_user.id): return await call.message.edit_text("👑 <b>Ты — админ!</b>\n\n<b>Безлимит</b> бесплатно.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")], [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    text = ("💎 <b>Выбери тариф</b>\n\n━━━━━━━━━━━━━━━\n\nОплата <b>подарком</b> владельцу.\n\n━━━━━━━━━━━━━━━")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Неделя — {PLANS['week']['stars']}⭐", callback_data="plan:week")],
        [InlineKeyboardButton(text=f"📅 2 недели — {PLANS['2weeks']['stars']}⭐", callback_data="plan:2weeks")],
        [InlineKeyboardButton(text=f"🗓 Месяц — {PLANS['month']['stars']}⭐", callback_data="plan:month")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("plan:"))
async def cb_plan(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    plan_id = call.data.split(":")[1]
    plan = PLANS[plan_id]
    
    text = (f"{plan['emoji']} <b>Тариф: {plan['name']}</b>\n\n💎 {plan['stars']}⭐\n📅 {plan['days']} дней\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n<b>Как оплатить:</b>\n"
            f"1️⃣ Нажми «🎁 Отправить подарок»\n2️⃣ Отправь подарок <b>от {plan['stars']}⭐</b> владельцу\n"
            f"3️⃣ Вернись и нажми «✅ Я оплатил»\n4️⃣ Дождись подтверждения админа")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Отправить подарок", url=get_profile_link())],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"pay_done:{plan_id}")],
        [InlineKeyboardButton(text="« Тарифы", callback_data="buy")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(F.data.startswith("pay_done:"))
async def cb_pay_done(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    plan_id = call.data.split(":")[1]
    plan = PLANS[plan_id]
    user = call.from_user

    if user_has_pending_request(user.id): return await call.answer("⏳ У тебя уже есть заявка на проверке!", show_alert=True)
    req_id = create_payment_request(user.id, user.username or "", user.full_name or "", plan_id)

    await call.message.edit_text(f"✅ <b>Заявка #{req_id} отправлена!</b>\n\n{plan['emoji']} <b>{plan['name']}</b> ({plan['stars']}⭐)\n\n⏳ Админ проверит оплату и активирует слот.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    kb_admin = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{req_id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{req_id}")]])
    try: await bot.send_message(OWNER_ID, f"💰 <b>Новая заявка #{req_id}</b>\n\n👤 @{user.username or '—'} (<code>{user.id}</code>)\n{plan['emoji']} <b>{plan['name']}</b> ({plan['stars']}⭐)", reply_markup=kb_admin, parse_mode="HTML")
    except: pass
    await call.answer("✅ Заявка отправлена")

@dp.callback_query(F.data == "upload")
async def cb_upload(call: types.CallbackQuery, state: FSMContext):
    if is_user_banned(call.from_user.id):
        return await call.answer("🚫 Заблокированы", show_alert=True)
    if not has_active_slot(call.from_user.id):
        return await call.answer("❌ Нет слота!", show_alert=True)

    await state.set_state(UploadStates.waiting_file)
    await call.message.edit_text(
        "📤 <b>Загрузка проекта</b>\n\n"
        "Отправь <b>.py</b> или <b>.zip</b> сюда в чат.\n\n"
        "Потом бот попросит токен (или <code>none</code>).\n"
        "📏 До 20 МБ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Отмена", callback_data="back_main")]
        ]),
        parse_mode="HTML",
    )
@dp.callback_query(F.data == "mybots")
async def cb_mybots(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bots = get_user_bots(call.from_user.id)
    if not bots: return await call.message.edit_text("🤖 <b>Нет ботов</b>\n\nЗагрузи первого!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")], [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    buttons = []
    for b in bots:
        status = "🟢" if b[0] in running_bots else "🔴"
        fname = b[2] if not str(b[2]).endswith(".zip") else "[ZIP Архив]"
        buttons.append([InlineKeyboardButton(text=f"{status} #{b[0]} • {fname}", callback_data=f"bot:{b[0]}")])
    buttons.append([InlineKeyboardButton(text="« Меню", callback_data="back_main")])
    await call.message.edit_text(f"🤖 <b>Твои боты ({len(bots)})</b>\n\n🟢 работает • 🔴 остановлен", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("bot:"))
async def cb_bot_detail(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)): return await call.answer("❌ Нет доступа", show_alert=True)

    status = "🟢 Работает" if bot_id in running_bots else "🔴 Остановлен"
    await call.message.edit_text(f"🤖 <b>Бот #{bot_id}</b>\n\n📁 Исходник: <code>{b[2]}</code>\n📊 Статус: {status}\n📅 {b[5][:10]}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Запуск", callback_data=f"start:{bot_id}"), InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stop:{bot_id}")],
            [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}"), InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{bot_id}")],
            [InlineKeyboardButton(text="« Список", callback_data="mybots")]]), parse_mode="HTML")

@dp.callback_query(F.data.startswith("start:"))
async def cb_start_bot(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id: return await call.answer("❌ Нет доступа", show_alert=True)
    if not has_active_slot(call.from_user.id): return await call.answer("❌ Нет слота", show_alert=True)
    if bot_id in running_bots: return await call.answer("⚠️ Уже запущен", show_alert=True)

    await call.answer("⏳ Запускаю проект (устанавливаю зависимости)...")
    if await start_user_bot(bot_id): await call.message.answer(f"✅ <b>Бот #{bot_id} запущен!</b>", parse_mode="HTML")
    else:
        logs_text = html.escape(get_bot_logs(bot_id, 40)[-2000:]) if get_bot_logs(bot_id, 40).strip() else "📭 Пусто"
        await call.message.answer(f"❌ <b>Бот #{bot_id} упал</b>\n\n<pre>{logs_text}</pre>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Снова", callback_data=f"start:{bot_id}")], [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}")], [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{bot_id}")], [InlineKeyboardButton(text="« Список", callback_data="mybots")]]))

@dp.callback_query(F.data.startswith("stop:"))
async def cb_stop_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id: return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    await call.answer("⏹ Остановлен")

@dp.callback_query(F.data.startswith("logs:"))
async def cb_logs(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)): return await call.answer("❌ Нет доступа", show_alert=True)

    logs_safe = html.escape(get_bot_logs(bot_id, 50)[-3000:])
    await call.message.answer(f"📄 <b>Логи #{bot_id}</b>\n\n<pre>{logs_safe}</pre>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"logs:{bot_id}")], [InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")]]), parse_mode="HTML")

@dp.callback_query(F.data.startswith("del:"))
async def cb_delete_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id: return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    
    import shutil
    bot_dir = BOTS_DIR / f"bot_{bot_id}"
    if bot_dir.exists(): shutil.rmtree(bot_dir, ignore_errors=True)
    delete_bot_record(bot_id)
    await call.answer("🗑 Удалён")
    await cb_mybots(call, None)

@dp.callback_query(F.data == "myslots")
async def cb_myslots(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.from_user.id == OWNER_ID or is_admin(call.from_user.id): return await call.message.edit_text("👑 <b>Безлимит</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    slots = get_active_slots(call.from_user.id)
    if not slots: return await call.message.edit_text("💳 <b>Нет активных слотов</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить", callback_data="buy")], [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    text = f"💳 <b>Слоты ({len(slots)})</b>\n\n"
    for s in slots:
        exp = datetime.fromisoformat(s[3])
        text += f"• <b>{PLANS[s[2]]['name']}</b> — ещё {(exp - datetime.now()).days} дн.\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить ещё", callback_data="buy")], [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

@dp.callback_query(F.data == "help")
async def cb_help(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = ("❓ <b>Помощь</b>\n\n<b>🎁 Как начать:</b>\n1. Нажми «💎 Купить слот» или введи промокод\n2. Отправь подарок владельцу (если покупаешь)\n"
            "3. Дождись подтверждения\n\n<b>📤 Загрузить бота:</b>\n1. Нажми «📤 Загрузить бота»\n"
            "2. Отправь .py файл или <b>.zip архив</b>\n3. Отправь токен (или 'none')\n4. Запусти через «🤖 Мои боты»\n\n"
            "💡 <i>В ZIP архив можно добавить файл <code>requirements.txt</code> — хостинг сам установит нужные пакеты!</i>")
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Владелец", url=get_profile_link())], [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML", disable_web_page_preview=True)

# ═══════════════════════════════════════════════════════════════
# 🔐 АДМИНКА
# ═══════════════════════════════════════════════════════════════

async def show_admin_panel(message, edit=False):
    s = get_stats()
    text = (f"🔐 <b>Админ-панель</b>\n\n━━━━━━━━━━━━━━━\n\n"
            f"👥 Users: <b>{s['total_users']}</b>\n🚫 Ban: <b>{s['banned']}</b>\n"
            f"🛡 Admins: <b>{s['admins']}</b>\n💳 Slots: <b>{s['active_slots']}</b>\n"
            f"🤖 Bots: <b>{s['total_bots']}</b> (🟢 {s['running_bots']})\n"
            f"💰 Ожидают оплаты: <b>{s['pending_reqs']}</b>")
    
    pay_text = "💰 Заявки 🔴" if s['pending_reqs'] > 0 else "💰 Заявки"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, callback_data="adm:payments"), InlineKeyboardButton(text="🎟 Промокоды", callback_data="adm:promos")],
        [InlineKeyboardButton(text="💾 Резервная копия БД", callback_data="adm:backup")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats"), InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="👥 Users", callback_data="adm:users")],
        [InlineKeyboardButton(text="🚫 Бан", callback_data="adm:ban"), InlineKeyboardButton(text="✅ Разбан", callback_data="adm:unban")],
        [InlineKeyboardButton(text="🛡 +Админ", callback_data="adm:addadmin"), InlineKeyboardButton(text="❌ -Админ", callback_data="adm:remadmin")],
        [InlineKeyboardButton(text="🔄 Рестарт всех", callback_data="adm:restart")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    if edit: await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else: await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    await show_admin_panel(call.message, edit=True)

@dp.callback_query(F.data == "adm:backup")
async def cb_adm_backup(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return await call.answer("Только владелец", show_alert=True)
    if os.path.exists(DB_PATH):
        await call.message.answer_document(FSInputFile(DB_PATH, filename=f"bothost_backup_{datetime.now().strftime('%Y%m%d')}.db"), caption="💾 Ваша база данных.\n\nЕсли сервер очистится, просто отправьте этот файл мне обратно, и я всё восстановлю!")
        await call.answer("✅ Бэкап отправлен!")
    else:
        await call.answer("❌ Файл базы не найден!", show_alert=True)

# --- АДМИНКА ПРОМОКОДОВ ---

@dp.callback_query(F.data == "adm:promos")
async def cb_adm_promos(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    promos = get_all_promos()
    text = "🎟 <b>Активные промокоды:</b>\n\n"
    buttons = [[InlineKeyboardButton(text="➕ Создать промокод", callback_data="adm:promo_add")]]
    
    if not promos: text += "Нет активных промокодов."
    else:
        for p in promos:
            text += f"• <code>{p[1]}</code> — {PLANS[p[2]]['name']} (Осталось: {p[3]})\n"
            buttons.append([InlineKeyboardButton(text=f"❌ Удалить {p[1]}", callback_data=f"adm:promo_del:{p[0]}")])
            
    buttons.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "adm:promo_add")
async def cb_adm_promo_add(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("🎟 <b>Создание промокода</b>\n\nОтправьте название промокода (на английском, без пробелов):", parse_mode="HTML")
    await state.set_state(AdminStates.promo_code)

@dp.message(AdminStates.promo_code)
async def adm_promo_code_step(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(code=code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Неделя", callback_data="adm:promo_plan:week")],
        [InlineKeyboardButton(text="📅 2 недели", callback_data="adm:promo_plan:2weeks")],
        [InlineKeyboardButton(text="🗓 Месяц", callback_data="adm:promo_plan:month")]])
    await message.answer(f"Промокод: <code>{code}</code>\n\nВыберите тариф, который он будет выдавать:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm:promo_plan:"))
async def adm_promo_plan_step(call: types.CallbackQuery, state: FSMContext):
    plan = call.data.split(":")[2]
    await state.update_data(plan=plan)
    await call.message.edit_text("Отправьте количество активаций (число):")
    await state.set_state(AdminStates.promo_uses)

@dp.message(AdminStates.promo_uses)
async def adm_promo_uses_step(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Отправьте число!")
    uses = int(message.text)
    data = await state.get_data()
    
    if create_promo(data['code'], data['plan'], uses):
        await message.answer(f"✅ <b>Промокод создан!</b>\n\nКод: <code>{data['code']}</code>\nАктиваций: {uses}\nТариф: {PLANS[data['plan']]['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К промокодам", callback_data="adm:promos")]]), parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка! Возможно, промокод с таким именем уже существует.")
    await state.clear()

@dp.callback_query(F.data.startswith("adm:promo_del:"))
async def cb_adm_promo_del(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    delete_promo(int(call.data.split(":")[2]))
    await call.answer("🗑 Удалено!")
    await cb_adm_promos(call)

# --- ОСТАЛЬНЫЕ КОМАНДЫ АДМИНА ---

@dp.callback_query(F.data == "adm:payments")
async def cb_adm_payments(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    reqs = get_pending_requests()
    if not reqs: return await call.message.edit_text("💰 <b>Нет заявок на ожидании</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")

    text = f"💰 <b>Заявки ({len(reqs)})</b>\n\n"
    buttons = []
    for r in reqs:
        plan = PLANS.get(r[4], {})
        uname = f"@{r[2]}" if r[2] else r[1]
        text += f"#{r[0]} {uname} — {plan.get('name', r[4])} ({plan.get('stars', '?')}⭐)\n"
        buttons.append([InlineKeyboardButton(text=f"✅ #{r[0]}", callback_data=f"approve:{r[0]}"), InlineKeyboardButton(text=f"❌ #{r[0]}", callback_data=f"reject:{r[0]}")])
    buttons.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    req_id = int(call.data.split(":")[1])
    req = get_payment_request(req_id)
    if not req or req[5] != "pending": return await call.answer("❌ Заявка не найдена или обработана", show_alert=True)

    user_id, username, plan = req[1], req[2], req[4]
    approve_payment(req_id)
    create_slot(user_id, plan)

    await call.message.edit_text(f"✅ <b>Заявка #{req_id} одобрена</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К заявкам", callback_data="adm:payments")]]), parse_mode="HTML")
    try: await bot.send_message(user_id, f"🎉 <b>Оплата подтверждена!</b>\nТеперь можешь загрузить бота!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")]]), parse_mode="HTML")
    except: pass
    await call.answer("✅ Одобрено")

@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    req_id = int(call.data.split(":")[1])
    req = get_payment_request(req_id)
    if not req or req[5] != "pending": return await call.answer("❌ Заявка не найдена", show_alert=True)

    user_id = req[1]
    reject_payment(req_id)

    await call.message.edit_text(f"❌ <b>Заявка #{req_id} отклонена</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К заявкам", callback_data="adm:payments")]]), parse_mode="HTML")
    try: await bot.send_message(user_id, f"❌ <b>Заявка отклонена</b>\nЕсли ты отправлял подарок — напиши владельцу.", parse_mode="HTML")
    except: pass
    await call.answer("❌ Отклонено")

@dp.callback_query(F.data == "adm:stats")
async def cb_adm_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    s = get_stats()
    await call.message.edit_text(f"📊 <b>Статистика</b>\n\n👥 {s['total_users']}\n🚫 {s['banned']}\n🛡 {s['admins']}\n💳 Слотов: {s['active_slots']}\n🤖 Ботов: {s['total_bots']} (🟢 {s['running_bots']})\n💰 Одобрено заявок: {s['approved_reqs']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")

@dp.callback_query(F.data == "adm:broadcast")
async def cb_adm_broadcast(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("📢 <b>Рассылка</b>\n\nОтправь текст.\nОтмена: /cancel", parse_mode="HTML")
    await state.set_state(AdminStates.broadcast)

@dp.callback_query(F.data == "adm:users")
async def cb_adm_users(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    users = get_all_users()[:15]
    text = f"👥 <b>Users ({len(get_all_users())})</b>\n\n"
    for u in users: text += f"{'🚫' if u[4] else '✓'}{'🛡' if u[3] else ''} <code>{u[0]}</code> @{u[1] or '—'}\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")

@dp.callback_query(F.data == "adm:ban")
async def cb_adm_ban(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("🚫 <b>Бан</b>\n\nID или @username\nОтмена: /cancel", parse_mode="HTML")
    await state.set_state(AdminStates.ban)

@dp.callback_query(F.data == "adm:unban")
async def cb_adm_unban(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text("✅ <b>Разбан</b>\n\nID\nОтмена: /cancel", parse_mode="HTML")
    await state.set_state(AdminStates.unban)

@dp.callback_query(F.data == "adm:addadmin")
async def cb_addadmin(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID: return await call.answer("⚠️ Только владелец", show_alert=True)
    await call.message.edit_text("🛡 <b>Добавить админа</b>\n\nID или @username\nОтмена: /cancel", parse_mode="HTML")
    await state.set_state(AdminStates.addadmin)

@dp.callback_query(F.data == "adm:remadmin")
async def cb_remadmin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return await call.answer("⚠️ Только владелец", show_alert=True)
    admins = get_all_admins()
    if not admins: return await call.answer("📭 Нет", show_alert=True)
    buttons = [[InlineKeyboardButton(text=f"❌ {a[1] or a[2] or a[0]}", callback_data=f"remadm:{a[0]}")] for a in admins]
    buttons.append([InlineKeyboardButton(text="« Отмена", callback_data="admin")])
    await call.message.edit_text("❌ <b>Удалить админа:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("remadm:"))
async def cb_remadm_confirm(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return
    remove_admin(int(call.data.split(":")[1]))
    await call.answer("✅ Удалён")
    await show_admin_panel(call.message, edit=True)

@dp.callback_query(F.data == "adm:restart")
async def cb_restart_all(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer("⏳ Перезапуск...")
    for bid in list(running_bots.keys()): await stop_user_bot(bid)

    restarted = 0
    for b in get_all_bots():
        bid, uid = b[0], b[1]
        if is_user_banned(uid): continue
        if uid != OWNER_ID and not is_admin(uid) and not has_active_slot(uid): continue
        bot_dir = BOTS_DIR / f"bot_{bid}"
        if bot_dir.exists():
            if await start_user_bot(bid): restarted += 1

    await call.message.answer(f"🔄 Перезапущено: {restarted}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]))

# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("=" * 50)
    logger.info("🤖 BotHost v4.2 (Cloud Backup & Promos) запущен")
    logger.info(f"👤 Владелец: {OWNER_ID}")
    logger.info("=" * 50)

    await restore_running_bots()
    asyncio.create_task(monitor_bots())
    asyncio.create_task(auto_backup())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("👋 Выход")
