"""
🤖 BotHost — хостинг Telegram-ботов (v5.0 PREMIUM)
✅ Все баги исправлены
✅ Файловый менеджер ботов
✅ Расширенные админ-функции
✅ Заморозка ботов
✅ Рассылка в ЛС конкретному юзеру
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
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ═══════════════════════════════════════════════════════════════
# 🔧 КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8711311188:AAHnhjvLhyYASMxUI-1hLyktHXhSsmYXnww")
OWNER_ID = 8269807543
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "ivan_unreal")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
BOTS_DIR = DATA_DIR / "bots"
DB_PATH = DATA_DIR / "bot.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BOTS_DIR.mkdir(parents=True, exist_ok=True)

PLANS = {
    "week":   {"name": "Неделя",    "stars": 15, "days": 7,  "emoji": "📅"},
    "2weeks": {"name": "2 недели",  "stars": 25, "days": 14, "emoji": "🗓"},
    "month":  {"name": "Месяц",     "stars": 50, "days": 30, "emoji": "💎"},
}

BOT_START_TIME = time.time()

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
    c.execute("""CREATE TABLE IF NOT EXISTS bots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT, bot_token TEXT, status TEXT DEFAULT 'stopped', created_at TEXT, is_frozen INTEGER DEFAULT 0, entry_point TEXT DEFAULT 'user_bot.py')""")
    c.execute("""CREATE TABLE IF NOT EXISTS payment_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, plan TEXT, status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, plan TEXT, uses_left INTEGER, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, promo_id INTEGER, UNIQUE(user_id, promo_id))""")
    
    # Миграция: добавляем колонки если их нет
    try:
        c.execute("ALTER TABLE bots ADD COLUMN is_frozen INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE bots ADD COLUMN entry_point TEXT DEFAULT 'user_bot.py'")
    except sqlite3.OperationalError: pass
    
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

def get_user(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone(); conn.close()
    return row

def find_user_by_username(username):
    username = username.lstrip("@").lower()
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username,))
    row = c.fetchone(); conn.close()
    return row[0] if row else None

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
    if is_admin(user_id): return [(0, user_id, "month", "2099-12-31", datetime.now().isoformat(), "admin")]
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

def save_bot(user_id, filename, user_bot_token, entry_point="user_bot.py"):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO bots (user_id, filename, bot_token, created_at, entry_point) VALUES (?, ?, ?, ?, ?)", (user_id, filename, user_bot_token, datetime.now().isoformat(), entry_point))
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

def update_bot_entry(bot_id, entry_point):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET entry_point = ? WHERE id = ?", (entry_point, bot_id))
    conn.commit(); conn.close()

def freeze_bot(bot_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET is_frozen = 1 WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def unfreeze_bot(bot_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET is_frozen = 0 WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def delete_bot_record(bot_id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def get_all_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots")
    rows = c.fetchall(); conn.close()
    return rows

def create_payment_request(user_id, username, full_name, plan):
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

def get_payment_request(req_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
    row = c.fetchone(); conn.close()
    return row

def approve_payment(req_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'approved', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), req_id))
    conn.commit(); conn.close()

def reject_payment(req_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'rejected', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), req_id))
    conn.commit(); conn.close()

def user_has_pending_request(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE user_id = ? AND status = 'pending'", (user_id,))
    count = c.fetchone()[0]; conn.close()
    return count > 0

def create_promo(code, plan, uses):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO promocodes (code, plan, uses_left, created_at) VALUES (?, ?, ?, ?)", (code, plan, uses, datetime.now().isoformat()))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError:
        conn.close(); return False

def get_all_promos():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, code, plan, uses_left FROM promocodes WHERE uses_left > 0")
    rows = c.fetchall(); conn.close()
    return rows

def delete_promo(promo_id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE id = ?", (promo_id,))
    conn.commit(); conn.close()

def use_promo(user_id, code):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, plan, uses_left FROM promocodes WHERE code = ?", (code,))
    promo = c.fetchone()
    if not promo or promo[2] <= 0:
        conn.close(); return False, "❌ Промокод не найден или закончился."
    c.execute("SELECT 1 FROM used_promos WHERE user_id = ? AND promo_id = ?", (user_id, promo[0]))
    if c.fetchone():
        conn.close(); return False, "⚠️ Ты уже использовал этот промокод."
    c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE id = ?", (promo[0],))
    c.execute("INSERT INTO used_promos (user_id, promo_id) VALUES (?, ?)", (user_id, promo[0]))
    conn.commit(); conn.close()
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
    c.execute("SELECT COUNT(*) FROM bots WHERE is_frozen = 1"); frozen = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"); pending_reqs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE status = 'approved'"); approved_reqs = c.fetchone()[0]
    conn.close()
    return {
        "total_users": total_users, "banned": banned, "admins": admins,
        "active_slots": active_slots, "total_bots": total_bots,
        "running_bots": len(running_bots), "frozen": frozen,
        "pending_reqs": pending_reqs, "approved_reqs": approved_reqs
    }

# ═══════════════════════════════════════════════════════════════
# 🛡 MIDDLEWARE — БЛОКИРОВКА ЗАБАНЕННЫХ (ГЛОБАЛЬНО)
# ═══════════════════════════════════════════════════════════════

class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and is_user_banned(user.id):
            try:
                if isinstance(event, types.Message):
                    await event.answer("🚫 <b>Вы заблокированы в BotHost</b>\n\nОбратитесь к владельцу.", parse_mode="HTML")
                elif isinstance(event, types.CallbackQuery):
                    await event.answer("🚫 Вы заблокированы", show_alert=True)
            except: pass
            return
        return await handler(event, data)

dp.message.middleware(BanMiddleware())
dp.callback_query.middleware(BanMiddleware())

# ═══════════════════════════════════════════════════════════════
# 🚀 WRAPPER
# ═══════════════════════════════════════════════════════════════

WRAPPER_CODE = '''#!/usr/bin/env python3
import os, sys, re, signal, subprocess, time

ENTRY_POINT = "{{ENTRY_POINT}}"

def log(msg): print(f"[BotHost] {msg}", flush=True)
log(f"Запуск. Исполняемый файл: {ENTRY_POINT}")

STDLIB_MODULES = {"os","sys","re","json","time","datetime","asyncio","logging","pathlib","typing","subprocess","signal","html","math","random","collections","itertools","functools","traceback","threading","queue","socket","urllib","http","email","base64","hashlib","hmac","uuid","sqlite3","csv","io","tempfile","shutil","copy","argparse","warnings","contextlib","dataclasses","enum","abc","inspect","operator","string","textwrap","unicodedata","struct","codecs","pickle","gzip","zipfile","tarfile","glob","fnmatch","builtins","statistics","secrets","ssl","calendar"}
PIP_MAPPING = {"telebot":"pyTelegramBotAPI","cv2":"opencv-python","PIL":"Pillow","yaml":"PyYAML","bs4":"beautifulsoup4","dotenv":"python-dotenv","telegram":"python-telegram-bot","discord":"discord.py"}

def is_installed(m):
    try: __import__(m); return True
    except: return False

if os.path.exists("requirements.txt"):
    log("Устанавливаем requirements.txt...")
    subprocess.run([sys.executable,"-m","pip","install","-r","requirements.txt","--quiet","--no-cache-dir"])
else:
    imports = set()
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and file != "wrapper.py":
                try:
                    with open(os.path.join(root,file),"r",encoding="utf-8") as f:
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
            subprocess.run([sys.executable,"-m","pip","install","--quiet","--no-cache-dir",PIP_MAPPING.get(mod,mod)])

process = None
def handle_signal(signum, frame):
    log("Выключение...")
    if process:
        process.terminate()
        try: process.wait(timeout=5)
        except: process.kill()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

if not os.path.exists(ENTRY_POINT):
    log(f"ОШИБКА: Файл {ENTRY_POINT} не найден!"); sys.exit(1)

log("🚀 Запуск!")
sys.stdout.flush()
process = subprocess.Popen([sys.executable,"-u",ENTRY_POINT], env=os.environ.copy())
while True:
    ret = process.poll()
    if ret is not None: sys.exit(ret)
    time.sleep(1)
'''

def write_wrapper(bot_dir, entry_point):
    wrapper_code = WRAPPER_CODE.replace("{{ENTRY_POINT}}", entry_point)
    (bot_dir / "wrapper.py").write_text(wrapper_code, encoding="utf-8")

async def start_user_bot(bot_id):
    try:
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        log_file = bot_dir / "bot.log"
        bot_data = get_bot(bot_id)
        if not bot_data: return False
        if bot_data[6] == 1:  # frozen
            return False
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
    except Exception as e:
        logger.error(f"start_user_bot error: {e}")
        return False

async def stop_user_bot(bot_id):
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

def get_bot_logs(bot_id, lines=50):
    log_file = BOTS_DIR / f"bot_{bot_id}" / "bot.log"
    if not log_file.exists(): return "📭 Логи пустые"
    try:
        content = log_file.read_text(encoding="utf-8", errors="ignore")
        return "\n".join(content.strip().split("\n")[-lines:]) or "📭 Логи пустые"
    except: return "❌ Ошибка чтения логов"

def list_bot_files(bot_id):
    bot_dir = BOTS_DIR / f"bot_{bot_id}"
    if not bot_dir.exists(): return []
    files = []
    for root, dirs, fs in os.walk(bot_dir):
        for f in fs:
            if f in ("wrapper.py", "bot.log"): continue
            full = Path(root) / f
            rel = full.relative_to(bot_dir)
            try:
                size = full.stat().st_size
            except: size = 0
            files.append((str(rel), size))
    return files

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
                    b = get_bot(bot_id)
                    if b:
                        uid = b[1]
                        if b[6] == 1:  # frozen
                            await stop_user_bot(bot_id)
                        elif uid != OWNER_ID and not is_admin(uid):
                            if is_user_banned(uid) or not has_active_slot(uid):
                                await stop_user_bot(bot_id)
        except Exception as e: logger.error(f"monitor error: {e}")
        await asyncio.sleep(30)

async def restore_running_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, user_id, is_frozen FROM bots WHERE status = 'running'")
    bots_to_restore = c.fetchall(); conn.close()
    for bot_id, user_id, frozen in bots_to_restore:
        if frozen: continue
        if is_user_banned(user_id): continue
        if user_id != OWNER_ID and not is_admin(user_id) and not has_active_slot(user_id): continue
        await start_user_bot(bot_id)

async def auto_backup():
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            if os.path.exists(DB_PATH):
                await bot.send_document(OWNER_ID, FSInputFile(DB_PATH, filename=f"bothost_backup_{datetime.now().strftime('%Y%m%d')}.db"), caption="🔄 Ежедневный авто-бэкап")
        except: pass

def get_uptime():
    seconds = int(time.time() - BOT_START_TIME)
    days, r = divmod(seconds, 86400)
    hours, r = divmod(r, 3600)
    minutes, _ = divmod(r, 60)
    return f"{days}д {hours}ч {minutes}м"

# ═══════════════════════════════════════════════════════════════
# 💬 ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════════

def get_profile_link():
    return f"https://t.me/{OWNER_USERNAME}" if OWNER_USERNAME else f"tg://user?id={OWNER_ID}"

WELCOME_TEXT = """✨ <b>Привет, {name}!</b>

Я — <b>BotHost 5.0</b> 💎
Профессиональный хостинг для Telegram-ботов.

━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>Возможности:</b>
• 📦 Загрузка <b>.zip / .py</b> файлов
• 🔧 Автоустановка библиотек
• 📁 Файловый менеджер
• 📊 Мониторинг в реальном времени
━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>Как начать?</b>
1️⃣ Купи слот или введи промокод
2️⃣ Отправь мне файл бота
3️⃣ Запусти и радуйся! 🎉"""

def main_menu_kb(user_id):
    buttons = [
        [InlineKeyboardButton(text="💎 Купить слот", callback_data="buy"), InlineKeyboardButton(text="🎟 Промокод", callback_data="promo_enter")],
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots"), InlineKeyboardButton(text="📊 Мои слоты", callback_data="myslots")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ]
    if is_admin(user_id): buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin")])
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
# 📝 FSM
# ═══════════════════════════════════════════════════════════════

class UploadStates(StatesGroup):
    waiting_file = State()
    waiting_token = State()

class AddFileStates(StatesGroup):
    waiting_file = State()

class UserStates(StatesGroup):
    enter_promo = State()

class AdminStates(StatesGroup):
    broadcast = State()
    broadcast_user_id = State()
    broadcast_user_msg = State()
    ban = State()
    unban = State()
    addadmin = State()
    promo_code = State()
    promo_uses = State()
    view_user = State()

# ═══════════════════════════════════════════════════════════════
# 📱 ХЕНДЛЕРЫ
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    create_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    await send_welcome(message)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.")

# ─── ФАЙЛЫ ──────────────────────────────────────────────────

@dp.message(F.document)
async def handle_file_universal(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    doc = message.document
    filename = doc.file_name or "bot.zip"
    ext = filename.lower().split('.')[-1]
    current_state = await state.get_state()

    logger.info(f"📥 [FILE] From {user_id}: {filename} ({doc.file_size} bytes) | state={current_state}")

    # === СЦЕНАРИЙ 1: Добавление файла к существующему боту ===
    if current_state == AddFileStates.waiting_file.state:
        data = await state.get_data()
        target_bot_id = data.get("target_bot_id")
        b = get_bot(target_bot_id)
        if not b or b[1] != user_id:
            await state.clear()
            return await message.answer("❌ Бот не найден.")
        
        bot_dir = BOTS_DIR / f"bot_{target_bot_id}"
        bot_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            file_info = await bot.get_file(doc.file_id)
            
            if ext == "zip":
                tmp_path = bot_dir / filename
                await bot.download_file(file_info.file_path, destination=tmp_path)
                with zipfile.ZipFile(tmp_path, 'r') as z:
                    z.extractall(bot_dir)
                tmp_path.unlink()
                await message.answer(f"✅ <b>Архив распакован!</b>\nФайлы добавлены к боту #{target_bot_id}", parse_mode="HTML")
            else:
                await bot.download_file(file_info.file_path, destination=bot_dir / filename)
                await message.answer(f"✅ <b>Файл {filename} добавлен!</b>\nК боту #{target_bot_id}", parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📁 К файлам", callback_data=f"files:{target_bot_id}")]]))
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")
        await state.clear()
        return

    # === СЦЕНАРИЙ 2: Восстановление БД для владельца ===
    if user_id == OWNER_ID and ext == "db" and current_state is None:
        await message.answer("⏳ Восстанавливаю базу данных...")
        try:
            file = await bot.get_file(doc.file_id)
            await bot.download_file(file.file_path, destination=DB_PATH)
            return await message.answer("✅ <b>База данных восстановлена!</b>", parse_mode="HTML")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: {e}")

    # === СЦЕНАРИЙ 3: Загрузка нового бота ===
    if not has_active_slot(user_id):
        return await message.answer(
            "❌ <b>Нет активного слота!</b>\n\nКупи слот или введи промокод.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить", callback_data="buy"), InlineKeyboardButton(text="🎟 Промокод", callback_data="promo_enter")]]),
            parse_mode="HTML")

    if ext not in ['py', 'zip']:
        return await message.answer("❌ Поддерживаются только <b>.py</b> и <b>.zip</b>", parse_mode="HTML")

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await message.answer("❌ Файл больше 20 МБ.")

    await state.update_data(file_id=doc.file_id, filename=filename, ext=ext)
    await state.set_state(UploadStates.waiting_token)
    await message.answer(
        f"✅ <b>Файл {filename} принят!</b>\n\n"
        f"🔑 Теперь отправь <b>токен бота</b> от @BotFather.\n"
        f"Если токен не нужен — напиши: <code>none</code>\n\n"
        f"🔒 <i>Сообщение с токеном будет удалено.</i>",
        parse_mode="HTML")

# ─── ТОКЕН ─────────────────────────────────────────────────

@dp.message(UploadStates.waiting_token, F.text)
async def handle_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    token_status = "🔐 Токен принят"
    if token.lower() in ["none", "нет", "no", "-", "skip", "нету"]:
        token = ""
        token_status = "🚫 Без токена"

    try: await message.delete()
    except: pass

    data = await state.get_data()
    file_id = data.get("file_id")
    ext = data.get("ext")
    filename = data.get("filename")

    if not file_id:
        await state.clear()
        return await message.answer("❌ Ошибка. Отправь файл заново.")

    status_msg = await message.answer("⏳ <i>Распаковываю файлы...</i>", parse_mode="HTML")

    try:
        entry_point = "user_bot.py"
        bot_id = save_bot(message.from_user.id, filename, token, entry_point)
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        bot_dir.mkdir(parents=True, exist_ok=True)

        file_info = await bot.get_file(file_id)
        download_path = bot_dir / filename
        await bot.download_file(file_info.file_path, destination=download_path)

        if ext == "zip":
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(bot_dir)
            download_path.unlink()

            possible_names = ['main.py', 'bot.py', 'app.py', 'run.py', '__main__.py']
            found = False
            for root, _, files in os.walk(bot_dir):
                for p in possible_names:
                    if p in files:
                        rel_dir = os.path.relpath(root, bot_dir)
                        entry_point = p if rel_dir == "." else f"{rel_dir}/{p}"
                        found = True; break
                if found: break
            if not found:
                for root, _, files in os.walk(bot_dir):
                    for f in files:
                        if f.endswith(".py"):
                            rel_dir = os.path.relpath(root, bot_dir)
                            entry_point = f if rel_dir == "." else f"{rel_dir}/{f}"
                            found = True; break
                    if found: break
        else:
            download_path.rename(bot_dir / "user_bot.py")

        update_bot_entry(bot_id, entry_point)
        write_wrapper(bot_dir, entry_point)

        await status_msg.edit_text(
            f"✅ <b>Бот развёрнут!</b>\n\n"
            f"🆔 ID: <code>{bot_id}</code>\n"
            f"📁 Точка входа: <code>{entry_point}</code>\n"
            f"{token_status}\n\n"
            f"🚀 Заходи в <b>«🤖 Мои боты»</b> и жми <b>▶️ Запуск</b>!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")]]),
            parse_mode="HTML")
    except Exception as e:
        logger.error(f"Save error: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка: {e}")
    await state.clear()

@dp.message(UploadStates.waiting_token)
async def handle_token_wrong(message: types.Message):
    await message.answer("⚠️ Отправь токен <b>текстом</b> или напиши <code>none</code>", parse_mode="HTML")

# ─── ПРОМОКОДЫ ─────────────────────────────────────

@dp.callback_query(F.data == "promo_enter")
async def cb_promo_enter(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.enter_promo)
    await call.message.edit_text(
        "🎟 <b>Ввод промокода</b>\n\nОтправь промокод сообщением:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="back_main")]]),
        parse_mode="HTML")

@dp.message(UserStates.enter_promo)
async def process_promo(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    success, result = use_promo(message.from_user.id, code)
    if success:
        plan_info = PLANS[result]
        await message.answer(
            f"🎉 <b>Промокод активирован!</b>\n\nТариф: {plan_info['emoji']} <b>{plan_info['name']}</b> ({plan_info['days']} дней).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]))
    else:
        await message.answer(result, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« В меню", callback_data="back_main")]]))
    await state.clear()

# ─── Callback ────────────────────────────────────

@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try: await call.message.delete()
    except: pass
    await send_welcome(call.message)

@dp.callback_query(F.data == "buy")
async def cb_buy(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.from_user.id == OWNER_ID or is_admin(call.from_user.id):
        return await call.message.edit_text(
            "👑 <b>Ты — админ!</b>\n\n<b>Безлимит</b> бесплатно 💎",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    text = "💎 <b>Выбери тариф</b>\n\n━━━━━━━━━━━━━━━\nОплата <b>подарком</b> владельцу ⭐"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Неделя — {PLANS['week']['stars']}⭐", callback_data="plan:week")],
        [InlineKeyboardButton(text=f"🗓 2 недели — {PLANS['2weeks']['stars']}⭐", callback_data="plan:2weeks")],
        [InlineKeyboardButton(text=f"💎 Месяц — {PLANS['month']['stars']}⭐", callback_data="plan:month")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("plan:"))
async def cb_plan(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    plan_id = call.data.split(":")[1]
    plan = PLANS[plan_id]
    text = (f"{plan['emoji']} <b>Тариф: {plan['name']}</b>\n\n"
            f"💎 {plan['stars']}⭐  •  📅 {plan['days']} дней\n\n━━━━━━━━━━━━━━━\n"
            f"<b>📋 Как оплатить:</b>\n1️⃣ Жми «🎁 Отправить подарок»\n"
            f"2️⃣ Отправь подарок <b>от {plan['stars']}⭐</b> владельцу\n"
            f"3️⃣ Вернись и нажми «✅ Я оплатил»\n4️⃣ Дождись подтверждения")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Отправить подарок", url=get_profile_link())],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"pay_done:{plan_id}")],
        [InlineKeyboardButton(text="« Тарифы", callback_data="buy")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(F.data.startswith("pay_done:"))
async def cb_pay_done(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    plan_id = call.data.split(":")[1]
    plan = PLANS[plan_id]
    user = call.from_user
    if user_has_pending_request(user.id): return await call.answer("⏳ У тебя уже есть заявка!", show_alert=True)
    req_id = create_payment_request(user.id, user.username or "", user.full_name or "", plan_id)
    await call.message.edit_text(
        f"✅ <b>Заявка #{req_id} отправлена!</b>\n\n{plan['emoji']} {plan['name']} ({plan['stars']}⭐)\n\n⏳ Ждём подтверждения админа.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
        parse_mode="HTML")
    kb_admin = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{req_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{req_id}")]])
    try: await bot.send_message(OWNER_ID, f"💰 <b>Новая заявка #{req_id}</b>\n\n👤 @{user.username or '—'} (<code>{user.id}</code>)\n{plan['emoji']} <b>{plan['name']}</b> ({plan['stars']}⭐)", reply_markup=kb_admin, parse_mode="HTML")
    except: pass

@dp.callback_query(F.data == "upload")
async def cb_upload(call: types.CallbackQuery, state: FSMContext):
    if not has_active_slot(call.from_user.id): return await call.answer("❌ Нет активного слота", show_alert=True)
    await state.set_state(UploadStates.waiting_file)
    await call.message.edit_text(
        "📤 <b>Загрузка проекта</b>\n\n"
        "Просто <b>отправь мне .py файл или .zip архив</b>.\n\n"
        "━━━━━━━━━━━━━━━\n📦 Для архивов: авто-поиск main.py и установка requirements.txt\n💡 Лимит: 20 МБ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="back_main")]]),
        parse_mode="HTML")

@dp.callback_query(F.data == "mybots")
async def cb_mybots(call: types.CallbackQuery, state: FSMContext = None):
    if state: await state.clear()
    bots = get_user_bots(call.from_user.id)
    if not bots:
        try:
            return await call.message.edit_text(
                "🤖 <b>У тебя пока нет ботов</b>\n\nЗагрузи первого!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")],
                    [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
                parse_mode="HTML")
        except: return

    buttons = []
    for b in bots:
        if b[0] in running_bots: status = "🟢"
        elif b[6] == 1: status = "🧊"
        else: status = "🔴"
        fname = b[2] if not str(b[2]).endswith(".zip") else "[📦 ZIP]"
        buttons.append([InlineKeyboardButton(text=f"{status} #{b[0]} • {fname[:30]}", callback_data=f"bot:{b[0]}")])
    buttons.append([InlineKeyboardButton(text="📤 Загрузить нового", callback_data="upload")])
    buttons.append([InlineKeyboardButton(text="« Меню", callback_data="back_main")])
    try:
        await call.message.edit_text(
            f"🤖 <b>Твои боты ({len(bots)})</b>\n\n🟢 работает • 🔴 остановлен • 🧊 заморожен",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("bot:"))
async def cb_bot_detail(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)

    if b[6] == 1: status = "🧊 Заморожен админом"
    elif bot_id in running_bots: status = "🟢 Работает"
    else: status = "🔴 Остановлен"

    text = (f"🤖 <b>Бот #{bot_id}</b>\n\n"
            f"📁 Исходник: <code>{b[2]}</code>\n"
            f"🚀 Точка входа: <code>{b[7] or 'user_bot.py'}</code>\n"
            f"📊 Статус: {status}\n"
            f"📅 Создан: {b[5][:10]}")

    buttons = [
        [InlineKeyboardButton(text="▶️ Запуск", callback_data=f"start:{bot_id}"),
         InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stop:{bot_id}")],
        [InlineKeyboardButton(text="🔄 Перезапуск", callback_data=f"restart:{bot_id}")],
        [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}"),
         InlineKeyboardButton(text="📁 Файлы", callback_data=f"files:{bot_id}")],
        [InlineKeyboardButton(text="➕ Добавить файл", callback_data=f"addfile:{bot_id}")],
        [InlineKeyboardButton(text="🗑 Удалить бота", callback_data=f"del:{bot_id}")],
    ]
    # Кнопки только для владельца/админа
    if is_admin(call.from_user.id) and b[1] != call.from_user.id:
        buttons.insert(0, [InlineKeyboardButton(text="👤 Инфо о владельце", callback_data=f"botowner:{bot_id}")])
    if is_admin(call.from_user.id):
        if b[6] == 1:
            buttons.append([InlineKeyboardButton(text="♨️ Разморозить", callback_data=f"unfreeze:{bot_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="🧊 Заморозить", callback_data=f"freeze:{bot_id}")])
    buttons.append([InlineKeyboardButton(text="« Список", callback_data="mybots")])

    try: await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except: await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("start:"))
async def cb_start_bot(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    if b[6] == 1: return await call.answer("🧊 Бот заморожен админом!", show_alert=True)
    if b[1] != OWNER_ID and not is_admin(b[1]) and not has_active_slot(b[1]):
        return await call.answer("❌ Нет слота", show_alert=True)
    if bot_id in running_bots: return await call.answer("⚠️ Уже запущен", show_alert=True)

    await call.answer("⏳ Запускаю...")
    if await start_user_bot(bot_id):
        await call.message.answer(f"✅ <b>Бот #{bot_id} запущен!</b>", parse_mode="HTML")
    else:
        logs_text = html.escape(get_bot_logs(bot_id, 40)[-2000:])
        await call.message.answer(
            f"❌ <b>Бот #{bot_id} упал</b>\n\n<pre>{logs_text}</pre>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data=f"start:{bot_id}")],
                [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}")],
                [InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")]]))

@dp.callback_query(F.data.startswith("stop:"))
async def cb_stop_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    await call.answer("⏹ Остановлен")

@dp.callback_query(F.data.startswith("restart:"))
async def cb_restart_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    if b[6] == 1: return await call.answer("🧊 Бот заморожен!", show_alert=True)
    await call.answer("🔄 Перезапуск...")
    await stop_user_bot(bot_id)
    await asyncio.sleep(2)
    if await start_user_bot(bot_id):
        await call.message.answer(f"🔄 <b>Бот #{bot_id} перезапущен!</b>", parse_mode="HTML")
    else:
        await call.message.answer(f"❌ Не удалось перезапустить #{bot_id}")

@dp.callback_query(F.data.startswith("freeze:"))
async def cb_freeze(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    bot_id = int(call.data.split(":")[1])
    freeze_bot(bot_id)
    await stop_user_bot(bot_id)
    b = get_bot(bot_id)
    if b:
        try: await bot.send_message(b[1], f"🧊 <b>Ваш бот #{bot_id} заморожен администратором.</b>\n\nОн не будет запускаться, пока админ не разморозит его.", parse_mode="HTML")
        except: pass
    await call.answer("🧊 Заморожен")
    await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("unfreeze:"))
async def cb_unfreeze(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    bot_id = int(call.data.split(":")[1])
    unfreeze_bot(bot_id)
    b = get_bot(bot_id)
    if b:
        try: await bot.send_message(b[1], f"♨️ <b>Ваш бот #{bot_id} разморожен!</b>\n\nМожете запускать.", parse_mode="HTML")
        except: pass
    await call.answer("♨️ Разморожен")
    await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("botowner:"))
async def cb_bot_owner(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b: return
    u = get_user(b[1])
    if u:
        text = f"👤 <b>Владелец бота #{bot_id}</b>\n\n🆔 <code>{u[0]}</code>\n👤 @{u[1] or '—'}\n📝 {u[2] or '—'}\n🚫 Забанен: {'Да' if u[4] else 'Нет'}"
    else:
        text = f"👤 ID: <code>{b[1]}</code>"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("logs:"))
async def cb_logs(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    logs_safe = html.escape(get_bot_logs(bot_id, 50)[-3000:])
    await call.message.answer(
        f"📄 <b>Логи #{bot_id}</b>\n\n<pre>{logs_safe}</pre>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")]]),
        parse_mode="HTML")

# ─── ФАЙЛОВЫЙ МЕНЕДЖЕР ─────────────────────────

@dp.callback_query(F.data.startswith("files:"))
async def cb_files(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)

    files = list_bot_files(bot_id)
    if not files:
        return await call.message.edit_text(
            f"📁 <b>Файлы бота #{bot_id}</b>\n\n📭 Пусто",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить файл", callback_data=f"addfile:{bot_id}")],
                [InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")]]),
            parse_mode="HTML")

    text = f"📁 <b>Файлы бота #{bot_id}</b>\n\nВсего: {len(files)}\n\n"
    buttons = []
    for i, (fname, size) in enumerate(files[:20]):
        size_kb = size / 1024
        text += f"• <code>{html.escape(fname)}</code> ({size_kb:.1f} KB)\n"
        buttons.append([
            InlineKeyboardButton(text=f"⬇️ {fname[:20]}", callback_data=f"getfile:{bot_id}:{i}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delfile:{bot_id}:{i}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data=f"addfile:{bot_id}")])
    buttons.append([InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")])

    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("getfile:"))
async def cb_getfile(call: types.CallbackQuery):
    _, bot_id, idx = call.data.split(":")
    bot_id, idx = int(bot_id), int(idx)
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    files = list_bot_files(bot_id)
    if idx >= len(files): return await call.answer("❌ Файл не найден", show_alert=True)
    fname, _ = files[idx]
    full = BOTS_DIR / f"bot_{bot_id}" / fname
    try:
        await call.message.answer_document(FSInputFile(str(full)), caption=f"📄 <code>{fname}</code>", parse_mode="HTML")
        await call.answer()
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("delfile:"))
async def cb_delfile(call: types.CallbackQuery):
    _, bot_id, idx = call.data.split(":")
    bot_id, idx = int(bot_id), int(idx)
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    files = list_bot_files(bot_id)
    if idx >= len(files): return await call.answer("❌ Не найдено", show_alert=True)
    fname, _ = files[idx]
    full = BOTS_DIR / f"bot_{bot_id}" / fname
    try:
        full.unlink()
        await call.answer(f"🗑 Удалён: {fname}")
        await cb_files(call, None)
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("addfile:"))
async def cb_addfile(call: types.CallbackQuery, state: FSMContext):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    await state.set_state(AddFileStates.waiting_file)
    await state.update_data(target_bot_id=bot_id)
    await call.message.edit_text(
        f"➕ <b>Добавить файл к боту #{bot_id}</b>\n\n"
        f"Отправь любой файл (или .zip архив — я его распакую).\n"
        f"Файлы добавятся к проекту.\n\n"
        f"❌ /cancel для отмены",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data=f"bot:{bot_id}")]]),
        parse_mode="HTML")

@dp.callback_query(F.data.startswith("del:"))
async def cb_delete_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    bot_dir = BOTS_DIR / f"bot_{bot_id}"
    if bot_dir.exists(): shutil.rmtree(bot_dir, ignore_errors=True)
    delete_bot_record(bot_id)
    await call.answer("🗑 Удалён")
    await cb_mybots(call)

@dp.callback_query(F.data == "myslots")
async def cb_myslots(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.from_user.id == OWNER_ID or is_admin(call.from_user.id):
        return await call.message.edit_text(
            "👑 <b>Безлимит для админов</b> 💎",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")
    slots = get_active_slots(call.from_user.id)
    if not slots:
        return await call.message.edit_text(
            "💳 <b>Нет активных слотов</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить", callback_data="buy")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")
    text = f"💳 <b>Мои слоты ({len(slots)})</b>\n\n"
    for s in slots:
        exp = datetime.fromisoformat(s[3])
        text += f"• <b>{PLANS[s[2]]['name']}</b> — ещё {(exp - datetime.now()).days} дн.\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить ещё", callback_data="buy")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

@dp.callback_query(F.data == "help")
async def cb_help(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = ("❓ <b>Помощь</b>\n\n"
            "<b>🎁 Как начать:</b>\n1. Купи слот или введи промокод\n"
            "2. Отправь подарок владельцу (при покупке)\n3. Жди подтверждения\n\n"
            "<b>📤 Загрузка бота:</b>\n1. Отправь .py или .zip\n2. Укажи токен (или 'none')\n"
            "3. Запусти через «🤖 Мои боты»\n\n"
            "<b>📁 Файловый менеджер:</b>\nМожно добавлять/удалять файлы к любому боту")
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Владелец", url=get_profile_link())],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
# 👑 АДМИНКА
# ═══════════════════════════════════════════════════════════════

async def show_admin_panel(message, edit=False):
    s = get_stats()
    text = (f"👑 <b>Админ-панель</b>\n\n━━━━━━━━━━━━━━━\n"
            f"👥 Юзеров: <b>{s['total_users']}</b>\n"
            f"🚫 Забанено: <b>{s['banned']}</b>\n"
            f"🛡 Админов: <b>{s['admins']}</b>\n"
            f"💳 Слотов: <b>{s['active_slots']}</b>\n"
            f"🤖 Ботов: <b>{s['total_bots']}</b> (🟢 {s['running_bots']} • 🧊 {s['frozen']})\n"
            f"💰 Заявок: <b>{s['pending_reqs']}</b>\n"
            f"⏱ Uptime: <b>{get_uptime()}</b>")
    pay_text = "💰 Заявки 🔴" if s['pending_reqs'] > 0 else "💰 Заявки"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, callback_data="adm:payments"),
         InlineKeyboardButton(text="🎟 Промокоды", callback_data="adm:promos")],
        [InlineKeyboardButton(text="💾 Бэкап БД", callback_data="adm:backup"),
         InlineKeyboardButton(text="🤖 Все боты", callback_data="adm:allbots")],
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="adm:broadcast"),
         InlineKeyboardButton(text="✉️ ЛС юзеру", callback_data="adm:msguser")],
        [InlineKeyboardButton(text="👥 Юзеры", callback_data="adm:users"),
         InlineKeyboardButton(text="🔍 Инфо о юзере", callback_data="adm:viewuser")],
        [InlineKeyboardButton(text="🚫 Бан", callback_data="adm:ban"),
         InlineKeyboardButton(text="✅ Разбан", callback_data="adm:unban")],
        [InlineKeyboardButton(text="🛡 +Админ", callback_data="adm:addadmin"),
         InlineKeyboardButton(text="❌ -Админ", callback_data="adm:remadmin")],
        [InlineKeyboardButton(text="🔄 Рестарт всех ботов", callback_data="adm:restart")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    if edit:
        try: await message.edit_text(text, reply_markup=kb, parse_mode="HTML"); return
        except: pass
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    await show_admin_panel(call.message, edit=True)

@dp.callback_query(F.data == "adm:allbots")
async def cb_adm_allbots(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐 Нет прав", show_alert=True)
    bots = get_all_bots()
    if not bots: return await call.message.edit_text("📭 Нет ботов", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]))
    text = f"🤖 <b>Все боты ({len(bots)})</b>\n\n"
    buttons = []
    for b in bots[:15]:
        if b[0] in running_bots: st = "🟢"
        elif b[6] == 1: st = "🧊"
        else: st = "🔴"
        buttons.append([InlineKeyboardButton(text=f"{st} #{b[0]} • user {b[1]}", callback_data=f"bot:{b[0]}")])
    buttons.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "adm:backup")
async def cb_adm_backup(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return await call.answer("Только владелец", show_alert=True)
    if os.path.exists(DB_PATH):
        await call.message.answer_document(FSInputFile(DB_PATH, filename=f"bothost_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"), caption="💾 Бэкап БД\n\nОтправь этот файл боту чтобы восстановить.")
        await call.answer("✅")
    else:
        await call.answer("❌ БД не найдена", show_alert=True)

@dp.callback_query(F.data == "adm:promos")
async def cb_adm_promos(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    promos = get_all_promos()
    text = "🎟 <b>Активные промокоды:</b>\n\n"
    buttons = [[InlineKeyboardButton(text="➕ Создать", callback_data="adm:promo_add")]]
    if not promos: text += "📭 Пусто"
    else:
        for p in promos:
            text += f"• <code>{p[1]}</code> — {PLANS[p[2]]['name']} (осталось: {p[3]})\n"
            buttons.append([InlineKeyboardButton(text=f"❌ {p[1]}", callback_data=f"adm:promo_del:{p[0]}")])
    buttons.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "adm:promo_add")
async def cb_adm_promo_add(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.promo_code)
    await call.message.edit_text("🎟 Отправь название промокода (латиница, без пробелов):", parse_mode="HTML")

@dp.message(AdminStates.promo_code)
async def adm_promo_code_step(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(code=code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Неделя", callback_data="adm:promo_plan:week")],
        [InlineKeyboardButton(text="🗓 2 недели", callback_data="adm:promo_plan:2weeks")],
        [InlineKeyboardButton(text="💎 Месяц", callback_data="adm:promo_plan:month")]])
    await message.answer(f"Промокод: <code>{code}</code>\n\nВыбери тариф:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm:promo_plan:"))
async def adm_promo_plan_step(call: types.CallbackQuery, state: FSMContext):
    plan = call.data.split(":")[2]
    await state.update_data(plan=plan)
    await state.set_state(AdminStates.promo_uses)
    await call.message.edit_text("Кол-во активаций (число):")

@dp.message(AdminStates.promo_uses)
async def adm_promo_uses_step(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Нужно число!")
    uses = int(message.text)
    data = await state.get_data()
    if create_promo(data['code'], data['plan'], uses):
        await message.answer(f"✅ Создан!\n\n<code>{data['code']}</code>\n{PLANS[data['plan']]['name']} × {uses}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К промокодам", callback_data="adm:promos")]]),
            parse_mode="HTML")
    else:
        await message.answer("❌ Такой промокод уже есть")
    await state.clear()

@dp.callback_query(F.data.startswith("adm:promo_del:"))
async def cb_adm_promo_del(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    delete_promo(int(call.data.split(":")[2]))
    await call.answer("🗑")
    await cb_adm_promos(call)

@dp.callback_query(F.data == "adm:payments")
async def cb_adm_payments(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    reqs = get_pending_requests()
    if not reqs: return await call.message.edit_text("💰 <b>Нет заявок</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")
    text = f"💰 <b>Заявки ({len(reqs)})</b>\n\n"
    buttons = []
    for r in reqs:
        plan = PLANS.get(r[4], {})
        uname = f"@{r[2]}" if r[2] else r[3]
        text += f"#{r[0]} {uname} — {plan.get('name', r[4])} ({plan.get('stars', '?')}⭐)\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{r[0]}", callback_data=f"approve:{r[0]}"),
            InlineKeyboardButton(text=f"❌ #{r[0]}", callback_data=f"reject:{r[0]}")])
    buttons.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐", show_alert=True)
    req_id = int(call.data.split(":")[1])
    req = get_payment_request(req_id)
    if not req or req[5] != "pending": return await call.answer("❌ Уже обработано", show_alert=True)
    approve_payment(req_id)
    create_slot(req[1], req[4])
    await call.message.edit_text(f"✅ Заявка #{req_id} одобрена", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К заявкам", callback_data="adm:payments")]]))
    try: await bot.send_message(req[1], f"🎉 <b>Оплата подтверждена!</b>\nМожешь загружать бота 🚀", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")]]), parse_mode="HTML")
    except: pass
    await call.answer("✅")

@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("🔐", show_alert=True)
    req_id = int(call.data.split(":")[1])
    req = get_payment_request(req_id)
    if not req or req[5] != "pending": return await call.answer("❌", show_alert=True)
    reject_payment(req_id)
    await call.message.edit_text(f"❌ #{req_id} отклонена", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К заявкам", callback_data="adm:payments")]]))
    try: await bot.send_message(req[1], "❌ <b>Заявка отклонена</b>\nЕсли оплачивал — напиши админу.", parse_mode="HTML")
    except: pass
    await call.answer("❌")

@dp.callback_query(F.data == "adm:broadcast")
async def cb_adm_broadcast(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text("📢 <b>Массовая рассылка</b>\n\nОтправь текст сообщения (HTML разрешён)\n/cancel — отмена", parse_mode="HTML")

@dp.message(AdminStates.broadcast)
async def adm_broadcast_send(message: types.Message, state: FSMContext):
    await state.clear()
    users = get_all_users()
    text = message.html_text or message.text
    ok, fail = 0, 0
    status = await message.answer(f"⏳ Отправка... ({len(users)} юзеров)")
    for u in users:
        try:
            await bot.send_message(u[0], text, parse_mode="HTML")
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ <b>Рассылка завершена</b>\n\nУспешно: {ok}\nОшибок: {fail}", parse_mode="HTML")

@dp.callback_query(F.data == "adm:msguser")
async def cb_adm_msguser(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.broadcast_user_id)
    await call.message.edit_text("✉️ <b>Сообщение в ЛС юзеру</b>\n\nОтправь ID или @username получателя:", parse_mode="HTML")

@dp.message(AdminStates.broadcast_user_id)
async def adm_msg_uid(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    target_id = None
    if txt.startswith("@"):
        target_id = find_user_by_username(txt)
        if not target_id: return await message.answer("❌ Юзер не найден. Попробуй по ID:")
    elif txt.isdigit():
        target_id = int(txt)
    else:
        return await message.answer("❌ Неверный формат. Пример: 123456789 или @username")
    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.broadcast_user_msg)
    await message.answer(f"✅ Юзер: <code>{target_id}</code>\n\nТеперь отправь текст сообщения:", parse_mode="HTML")

@dp.message(AdminStates.broadcast_user_msg)
async def adm_msg_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("target_id")
    await state.clear()
    try:
        await bot.send_message(target, f"✉️ <b>Сообщение от администратора:</b>\n\n{message.html_text or message.text}", parse_mode="HTML")
        await message.answer(f"✅ Отправлено юзеру <code>{target}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data == "adm:viewuser")
async def cb_adm_viewuser(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.view_user)
    await call.message.edit_text("🔍 Отправь ID или @username юзера:", parse_mode="HTML")

@dp.message(AdminStates.view_user)
async def adm_view_user(message: types.Message, state: FSMContext):
    await state.clear()
    txt = message.text.strip()
    uid = None
    if txt.startswith("@"): uid = find_user_by_username(txt)
    elif txt.isdigit(): uid = int(txt)
    if not uid: return await message.answer("❌ Юзер не найден")
    u = get_user(uid)
    if not u: return await message.answer("❌ Юзер не найден в БД")
    slots = get_active_slots(uid)
    bots = get_user_bots(uid)
    text = (f"👤 <b>Юзер</b>\n\n🆔 <code>{u[0]}</code>\n📛 @{u[1] or '—'}\n📝 {u[2] or '—'}\n"
            f"🛡 Админ: {'Да' if u[3] else 'Нет'}\n🚫 Бан: {'Да' if u[4] else 'Нет'}\n"
            f"📅 Регистрация: {u[5][:10]}\n\n"
            f"💳 Активных слотов: {len(slots)}\n🤖 Ботов: {len(bots)}")
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data == "adm:stats")
async def cb_adm_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    await show_admin_panel(call.message, edit=True)

@dp.callback_query(F.data == "adm:users")
async def cb_adm_users(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    users = get_all_users()[:20]
    text = f"👥 <b>Юзеры (последние 20 из {len(get_all_users())})</b>\n\n"
    for u in users: text += f"{'🚫' if u[4] else '✓'}{'🛡' if u[3] else ''} <code>{u[0]}</code> @{u[1] or '—'}\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")

@dp.callback_query(F.data == "adm:ban")
async def cb_adm_ban(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.ban)
    await call.message.edit_text("🚫 Отправь ID или @username для бана\n/cancel — отмена", parse_mode="HTML")

@dp.message(AdminStates.ban)
async def adm_ban_do(message: types.Message, state: FSMContext):
    await state.clear()
    txt = message.text.strip()
    uid = None
    if txt.startswith("@"): uid = find_user_by_username(txt)
    elif txt.isdigit(): uid = int(txt)
    if not uid: return await message.answer("❌ Не найден")
    if uid == OWNER_ID: return await message.answer("❌ Нельзя")
    ban_user(uid)
    # Остановка всех ботов юзера
    for b in get_user_bots(uid):
        await stop_user_bot(b[0])
    await message.answer(f"🚫 Забанен <code>{uid}</code>\nЕго боты остановлены.", parse_mode="HTML")

@dp.callback_query(F.data == "adm:unban")
async def cb_adm_unban(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.unban)
    await call.message.edit_text("✅ Отправь ID для разбана\n/cancel", parse_mode="HTML")

@dp.message(AdminStates.unban)
async def adm_unban_do(message: types.Message, state: FSMContext):
    await state.clear()
    txt = message.text.strip()
    uid = None
    if txt.startswith("@"): uid = find_user_by_username(txt)
    elif txt.isdigit(): uid = int(txt)
    if not uid: return await message.answer("❌ Не найден")
    unban_user(uid)
    await message.answer(f"✅ Разбанен <code>{uid}</code>", parse_mode="HTML")

@dp.callback_query(F.data == "adm:addadmin")
async def cb_addadmin(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID: return await call.answer("⚠️ Только владелец", show_alert=True)
    await state.set_state(AdminStates.addadmin)
    await call.message.edit_text("🛡 Отправь ID или @username\n/cancel", parse_mode="HTML")

@dp.message(AdminStates.addadmin)
async def adm_addadmin_do(message: types.Message, state: FSMContext):
    await state.clear()
    txt = message.text.strip()
    uid = None
    if txt.startswith("@"): uid = find_user_by_username(txt)
    elif txt.isdigit(): uid = int(txt)
    if not uid: return await message.answer("❌")
    add_admin(uid)
    await message.answer(f"🛡 Добавлен админ <code>{uid}</code>", parse_mode="HTML")

@dp.callback_query(F.data == "adm:remadmin")
async def cb_remadmin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return await call.answer("⚠️", show_alert=True)
    admins = get_all_admins()
    if not admins: return await call.answer("📭", show_alert=True)
    buttons = [[InlineKeyboardButton(text=f"❌ {a[1] or a[2] or a[0]}", callback_data=f"remadm:{a[0]}")] for a in admins]
    buttons.append([InlineKeyboardButton(text="« Отмена", callback_data="admin")])
    await call.message.edit_text("❌ Кого удалить?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("remadm:"))
async def cb_remadm_confirm(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return
    remove_admin(int(call.data.split(":")[1]))
    await call.answer("✅")
    await show_admin_panel(call.message, edit=True)

@dp.callback_query(F.data == "adm:restart")
async def cb_restart_all(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer("⏳ Перезапускаем...")
    for bid in list(running_bots.keys()): await stop_user_bot(bid)
    restarted = 0
    for b in get_all_bots():
        bid, uid = b[0], b[1]
        if b[6] == 1: continue
        if is_user_banned(uid): continue
        if uid != OWNER_ID and not is_admin(uid) and not has_active_slot(uid): continue
        if (BOTS_DIR / f"bot_{bid}").exists():
            if await start_user_bot(bid): restarted += 1
    await call.message.answer(f"🔄 Перезапущено: {restarted}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]))

# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("=" * 50)
    logger.info("🤖 BotHost v5.0 PREMIUM запущен")
    logger.info(f"👤 Владелец: {OWNER_ID}")
    logger.info("=" * 50)
    await restore_running_bots()
    asyncio.create_task(monitor_bots())
    asyncio.create_task(auto_backup())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("👋 Выход")
