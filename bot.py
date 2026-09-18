"""
🤖 BotHost v6.0 Ultimate (AI & GodMode & Env Manager)
✅ ПОЛНЫЙ ФУНКЦИОНАЛ: Все старые + все новые фичи
✅ Авто-бэкапы БД раз в сутки + ручной скач бэкапа админом
✅ Подтверждение оплаты (звёзды/подарки) и система слотов
✅ Промокоды (создание, удаление, использование)
✅ ИИ-дебаггер ошибок на базе Groq (Llama-3-70B)
✅ Управление файлами бота + редактирование .env
✅ God Mode для админа: доступ ко ВСЕМ ботам и файлам на хосте
✅ Фоновый мониторинг падений и авто-перезапуск при рестарте
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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════
# 🔧 КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8711311188:AAHnhjvLhyYASMxUI-1hLyktHXhSsmYXnww")
OWNER_ID = int(os.environ.get("OWNER_ID", "8269807543"))
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "ivan_unreal")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

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

groq_client = AsyncGroq(api_key=GROQ_API_KEY) if (GROQ_AVAILABLE and GROQ_API_KEY) else None

# ═══════════════════════════════════════════════════════════════
# 💾 БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT, expires_at TEXT, created_at TEXT, gift_id TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT, bot_token TEXT, status TEXT DEFAULT 'stopped', created_at TEXT, is_frozen INTEGER DEFAULT 0, entry_point TEXT DEFAULT 'user_bot.py')""")
    c.execute("""CREATE TABLE IF NOT EXISTS payment_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, full_name TEXT, plan TEXT, status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, plan TEXT, uses_left INTEGER, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, promo_id INTEGER, UNIQUE(user_id, promo_id))""")
    try: c.execute("ALTER TABLE bots ADD COLUMN is_frozen INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE bots ADD COLUMN entry_point TEXT DEFAULT 'user_bot.py'")
    except: pass
    conn.commit(); conn.close()

def get_db(): return sqlite3.connect(DB_PATH)

def create_user(uid, uname, fname=""):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username = ?, full_name = ?", (uid, uname, fname, datetime.now().isoformat(), uname, fname))
    conn.commit(); conn.close()

def get_user(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    r = c.fetchone(); conn.close(); return r

def get_all_users():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    r = c.fetchall(); conn.close(); return r

def find_user_by_username(uname):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (uname.lstrip("@").lower(),))
    r = c.fetchone(); conn.close(); return r[0] if r else None

def is_user_banned(uid):
    if uid == OWNER_ID: return False
    u = get_user(uid)
    return bool(u and u[4])

def ban_user(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def unban_user(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def is_admin(uid):
    if uid == OWNER_ID: return True
    u = get_user(uid)
    return bool(u and u[3])

def add_admin(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)", (uid, datetime.now().isoformat()))
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def remove_admin(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (uid,))
    conn.commit(); conn.close()

def get_all_admins():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 1 AND user_id != ?", (OWNER_ID,))
    r = c.fetchall(); conn.close(); return r

def has_active_slot(uid):
    if is_admin(uid): return True
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM slots WHERE user_id = ? AND expires_at > ?", (uid, datetime.now().isoformat()))
    r = c.fetchone()[0]; conn.close(); return r > 0

def get_active_slots(uid):
    if is_admin(uid): return [(0, uid, "month", "2099-12-31", datetime.now().isoformat(), "admin")]
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM slots WHERE user_id = ? AND expires_at > ?", (uid, datetime.now().isoformat()))
    r = c.fetchall(); conn.close(); return r

def create_slot(uid, plan):
    exp = datetime.now() + timedelta(days=PLANS[plan]["days"])
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO slots (user_id, plan, expires_at, created_at) VALUES (?, ?, ?, ?)", (uid, plan, exp.isoformat(), datetime.now().isoformat()))
    conn.commit(); conn.close()

def save_bot(uid, fname, token, ep="user_bot.py"):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO bots (user_id, filename, bot_token, created_at, entry_point) VALUES (?, ?, ?, ?, ?)", (uid, fname, token, datetime.now().isoformat(), ep))
    bid = c.lastrowid; conn.commit(); conn.close(); return bid

def get_user_bots(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE user_id = ?", (uid,))
    r = c.fetchall(); conn.close(); return r

def get_bot(bid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE id = ?", (bid,))
    r = c.fetchone(); conn.close(); return r

def get_all_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM bots")
    r = c.fetchall(); conn.close(); return r

def update_bot_entry(bid, ep):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET entry_point = ? WHERE id = ?", (ep, bid))
    conn.commit(); conn.close()

def freeze_bot(bid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET is_frozen = 1 WHERE id = ?", (bid,))
    conn.commit(); conn.close()

def unfreeze_bot(bid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET is_frozen = 0 WHERE id = ?", (bid,))
    conn.commit(); conn.close()

def delete_bot_record(bid):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM bots WHERE id = ?", (bid,))
    conn.commit(); conn.close()

def create_payment_request(uid, uname, fname, plan):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO payment_requests (user_id, username, full_name, plan, created_at) VALUES (?, ?, ?, ?, ?)", (uid, uname, fname, plan, datetime.now().isoformat()))
    rid = c.lastrowid; conn.commit(); conn.close(); return rid

def get_pending_requests():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM payment_requests WHERE status = 'pending' ORDER BY created_at ASC")
    r = c.fetchall(); conn.close(); return r

def get_payment_request(rid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM payment_requests WHERE id = ?", (rid,))
    r = c.fetchone(); conn.close(); return r

def approve_payment(rid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'approved', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), rid))
    conn.commit(); conn.close()

def reject_payment(rid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE payment_requests SET status = 'rejected', processed_at = ? WHERE id = ?", (datetime.now().isoformat(), rid))
    conn.commit(); conn.close()

def user_has_pending_request(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM payment_requests WHERE user_id = ? AND status = 'pending'", (uid,))
    r = c.fetchone()[0]; conn.close(); return r > 0

def create_promo(code, plan, uses):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO promocodes (code, plan, uses_left, created_at) VALUES (?, ?, ?, ?)", (code, plan, uses, datetime.now().isoformat()))
        conn.commit(); conn.close(); return True
    except:
        conn.close(); return False

def get_all_promos():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, code, plan, uses_left FROM promocodes WHERE uses_left > 0")
    r = c.fetchall(); conn.close(); return r

def delete_promo(pid):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE id = ?", (pid,))
    conn.commit(); conn.close()

def use_promo(uid, code):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, plan, uses_left FROM promocodes WHERE code = ?", (code,))
    p = c.fetchone()
    if not p or p[2] <= 0: conn.close(); return False, "❌ Промокод не найден или закончился."
    c.execute("SELECT 1 FROM used_promos WHERE user_id = ? AND promo_id = ?", (uid, p[0]))
    if c.fetchone(): conn.close(); return False, "⚠️ Ты уже использовал этот промокод."
    c.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE id = ?", (p[0],))
    c.execute("INSERT INTO used_promos (user_id, promo_id) VALUES (?, ?)", (uid, p[0]))
    conn.commit(); conn.close(); create_slot(uid, p[1]); return True, p[1]

def get_stats():
    conn = get_db(); c = conn.cursor()
    r = {
        "users": c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "banned": c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0],
        "admins": c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0],
        "slots": c.execute("SELECT COUNT(*) FROM slots WHERE expires_at > ?", (datetime.now().isoformat(),)).fetchone()[0],
        "bots": c.execute("SELECT COUNT(*) FROM bots").fetchone()[0],
        "frozen": c.execute("SELECT COUNT(*) FROM bots WHERE is_frozen = 1").fetchone()[0],
        "pending": c.execute("SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'").fetchone()[0],
        "running": len(running_bots)
    }
    conn.close(); return r

# ═══════════════════════════════════════════════════════════════
# 🛡 MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        u = data.get("event_from_user")
        if u and is_user_banned(u.id):
            if isinstance(event, types.Message):
                await event.answer("🚫 <b>Вы заблокированы на хостинге.</b>", parse_mode="HTML")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("🚫 Вы заблокированы", show_alert=True)
            return
        return await handler(event, data)

dp.message.middleware(BanMiddleware())
dp.callback_query.middleware(BanMiddleware())

# ═══════════════════════════════════════════════════════════════
# 🚀 WRAPPER И МОНИТОРИНГ
# ═══════════════════════════════════════════════════════════════

WRAPPER_CODE = '''#!/usr/bin/env python3
import os, sys, re, signal, subprocess, time

ENTRY_POINT = "{{ENTRY_POINT}}"

def log(msg): print(f"[BotHost] {msg}", flush=True)

if os.path.exists("requirements.txt"):
    log("📦 Установка пакетов из requirements.txt...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet", "--no-cache-dir"])

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

log(f"🚀 Запуск процесса: {ENTRY_POINT}")
sys.stdout.flush()

env = os.environ.copy()
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip("'\\"")

process = subprocess.Popen([sys.executable, "-u", ENTRY_POINT], env=env)
while True:
    ret = process.poll()
    if ret is not None: sys.exit(ret)
    time.sleep(1)
'''

def write_wrapper(bot_dir, entry_point):
    (bot_dir / "wrapper.py").write_text(WRAPPER_CODE.replace("{{ENTRY_POINT}}", entry_point), encoding="utf-8")

async def start_user_bot(bot_id):
    try:
        b = get_bot(bot_id)
        if not b or b[6] == 1: return False
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        log_file = bot_dir / "bot.log"
        
        env = os.environ.copy()
        if b[3]: env["BOT_TOKEN"] = b[3]
        env["PYTHONUNBUFFERED"] = "1"

        with open(log_file, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen([sys.executable, "-u", "wrapper.py"], cwd=str(bot_dir), env=env, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)

        running_bots[bot_id] = proc
        await asyncio.sleep(5)
        if proc.poll() is not None:
            del running_bots[bot_id]
            conn = get_db(); c = conn.cursor()
            c.execute("UPDATE bots SET status = 'error' WHERE id = ?", (bot_id,))
            conn.commit(); conn.close()
            return False

        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
        conn.commit(); conn.close()
        return True
    except: return False

async def stop_user_bot(bot_id):
    if bot_id in running_bots:
        proc = running_bots.pop(bot_id)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=3)
        except:
            try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except: pass
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()

def get_bot_logs(bot_id, lines=50):
    lf = BOTS_DIR / f"bot_{bot_id}" / "bot.log"
    if not lf.exists(): return ""
    try:
        return "\n".join(lf.read_text(encoding="utf-8", errors="ignore").strip().split("\n")[-lines:])
    except: return ""

def list_bot_files(bot_id):
    bot_dir = BOTS_DIR / f"bot_{bot_id}"
    if not bot_dir.exists(): return []
    files = []
    for root, _, fs in os.walk(bot_dir):
        for f in fs:
            if f in ("wrapper.py", "bot.log"): continue
            full = Path(root) / f
            rel = full.relative_to(bot_dir)
            try: sz = full.stat().st_size
            except: sz = 0
            files.append((str(rel), sz))
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
                        try: await bot.send_message(row[0], f"⚠️ <b>Бот #{bot_id} упал!</b>\nКод: {code}\n<pre>{html.escape(logs[-500:])}</pre>", parse_mode="HTML")
                        except: pass
                else:
                    b = get_bot(bot_id)
                    if b:
                        uid = b[1]
                        if b[6] == 1 or is_user_banned(uid) or (uid != OWNER_ID and not is_admin(uid) and not has_active_slot(uid)):
                            await stop_user_bot(bot_id)
        except Exception as e: logger.error(f"monitor error: {e}")
        await asyncio.sleep(30)

async def restore_running_bots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, user_id, is_frozen FROM bots WHERE status = 'running'")
    bots_to_restore = c.fetchall(); conn.close()
    for bot_id, user_id, frozen in bots_to_restore:
        if frozen or is_user_banned(user_id): continue
        if user_id != OWNER_ID and not is_admin(user_id) and not has_active_slot(user_id): continue
        await start_user_bot(bot_id)

async def auto_backup():
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            if os.path.exists(DB_PATH):
                await bot.send_document(OWNER_ID, FSInputFile(DB_PATH, filename=f"bothost_backup_{datetime.now().strftime('%Y%m%d')}.db"), caption="🔄 Автоматический суточный бэкап базы данных.")
        except: pass

# ═══════════════════════════════════════════════════════════════
# 🧠 AI ИИ-ДЕБАГГЕР (GROQ)
# ═══════════════════════════════════════════════════════════════

async def analyze_with_groq(logs):
    if not groq_client: return "❌ **AI-дебаггер недоступен.**\nНа сервере не настроен `GROQ_API_KEY`."
    if not logs.strip(): return "📭 Логи пустые, нечего анализировать."

    system_prompt = (
        "Ты — опытный Python разработчик хостинга BotHost. Проанализируй лог ошибки бота и помоги пользователю её исправить.\n"
        "Отвечай строго в формате HTML:\n"
        "1. <b>❓ В чём ошибка:</b> (Объясни понятным языком)\n"
        "2. <b>📍 Где проблема:</b> (Укажи файл и строку, если есть)\n"
        "3. <b>💡 Как исправить:</b> (Дай готовый код или команду)"
    )

    try:
        response = await groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Лог:\n\n{logs[-2500:]}"}],
            model="llama3-70b-8192", temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e: return f"❌ Ошибка нейросети: {e}"

# ═══════════════════════════════════════════════════════════════
# 📝 FSM И СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════

class UploadStates(StatesGroup): waiting_file = State(); waiting_token = State()
class AddFileStates(StatesGroup): waiting_file = State()
class EnvStates(StatesGroup): waiting_env_text = State()
class UserStates(StatesGroup): enter_promo = State()
class AdminStates(StatesGroup):
    broadcast = State(); msg_uid = State(); msg_text = State()
    view_user = State(); addadmin = State(); ban = State(); unban = State()
    promo_code = State(); promo_uses = State()

# ═══════════════════════════════════════════════════════════════
# 📱 ИНТЕРФЕЙС И КНОПКИ
# ═══════════════════════════════════════════════════════════════

def get_profile_link(): return f"https://t.me/{OWNER_USERNAME}" if OWNER_USERNAME else f"tg://user?id={OWNER_ID}"

def main_menu_kb(uid):
    buttons = [
        [InlineKeyboardButton(text="💎 Купить слот", callback_data="buy"), InlineKeyboardButton(text="🎟 Промокод", callback_data="promo_enter")],
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots"), InlineKeyboardButton(text="📊 Мои слоты", callback_data="myslots")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    if is_admin(uid): buttons.append([InlineKeyboardButton(text="👑 Панель управления", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_uptime():
    sec = int(time.time() - BOT_START_TIME)
    d, r = divmod(sec, 86400); h, r = divmod(r, 3600); m, _ = divmod(r, 60)
    return f"{d}д {h}ч {m}м"

# ═══════════════════════════════════════════════════════════════
# 🎯 ХЕНДЛЕРЫ ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    create_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
    text = (f"👋 <b>Привет, {html.escape(message.from_user.first_name)}!</b>\n\n"
            f"Добро пожаловать в <b>BotHost v6.0 AI</b> 💎\n\n"
            f"🚀 <b>Возможности:</b>\n"
            f"• Хостинг Telegram и Discord ботов на Python\n"
            f"• 🧠 <b>ИИ-дебаггер:</b> автоматически ищет ошибки в коде\n"
            f"• ⚙️ <b>Редактор окружения:</b> настройка `.env` прямо в чате\n"
            f"• 📦 Распаковка `.zip` архивов и автоустановка библиотек")
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear(); await message.answer("❌ Действие отменено.")

# ─── ПРИЕМ ФАЙЛОВ ─────────────────────────────────────────────

@dp.message(F.document)
async def handle_files(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    doc = message.document
    fname = doc.file_name or "bot.zip"
    ext = fname.lower().split('.')[-1]
    curr_state = await state.get_state()

    if curr_state == AddFileStates.waiting_file.state:
        data = await state.get_data(); target_bid = data.get("target_bid"); b = get_bot(target_bid)
        if not b or (b[1] != uid and not is_admin(uid)):
            await state.clear(); return await message.answer("❌ Доступ запрещен.")

        bot_dir = BOTS_DIR / f"bot_{target_bid}"; bot_dir.mkdir(parents=True, exist_ok=True)
        try:
            finfo = await bot.get_file(doc.file_id)
            if ext == "zip":
                tmp = bot_dir / fname
                await bot.download_file(finfo.file_path, destination=tmp)
                with zipfile.ZipFile(tmp, 'r') as z: z.extractall(bot_dir)
                tmp.unlink()
                await message.answer(f"✅ <b>Архив распакован в бота #{target_bid}!</b>", parse_mode="HTML")
            else:
                await bot.download_file(finfo.file_path, destination=bot_dir / fname)
                await message.answer(f"✅ <b>Файл {fname} загружен в бота #{target_bid}!</b>", parse_mode="HTML")
        except Exception as e: await message.answer(f"❌ Ошибка: {e}")
        await state.clear(); return

    if uid == OWNER_ID and ext == "db" and not curr_state:
        try:
            finfo = await bot.get_file(doc.file_id)
            await bot.download_file(finfo.file_path, destination=DB_PATH)
            return await message.answer("✅ <b>База данных успешно восстановлена!</b>", parse_mode="HTML")
        except Exception as e: return await message.answer(f"❌ Ошибка: {e}")

    if not has_active_slot(uid):
        return await message.answer("❌ <b>У тебя нет активного слота!</b>\nКупи слот или активируй промокод.", parse_mode="HTML")

    if ext not in ['py', 'zip']: return await message.answer("❌ Принимаются только файлы <b>.py</b> и <b>.zip</b>", parse_mode="HTML")

    await state.update_data(file_id=doc.file_id, fname=fname, ext=ext)
    await state.set_state(UploadStates.waiting_token)
    await message.answer(f"✅ <b>Файл {fname} получен!</b>\n\nОтправь <b>токен бота</b> от @BotFather (или напиши <code>none</code>):", parse_mode="HTML")

@dp.message(UploadStates.waiting_token, F.text)
async def handle_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if token.lower() in ["none", "нет", "no", "-", "skip"]: token = ""
    try: await message.delete()
    except: pass

    data = await state.get_data()
    msg = await message.answer("⏳ <i>Распаковка и подготовка проекта...</i>", parse_mode="HTML")
    try:
        ep = "user_bot.py"
        bid = save_bot(message.from_user.id, data['fname'], token, ep)
        bot_dir = BOTS_DIR / f"bot_{bid}"; bot_dir.mkdir(parents=True, exist_ok=True)

        finfo = await bot.get_file(data['file_id'])
        dpath = bot_dir / data['fname']
        await bot.download_file(finfo.file_path, destination=dpath)

        if data['ext'] == "zip":
            with zipfile.ZipFile(dpath, 'r') as z: z.extractall(bot_dir)
            dpath.unlink()
            for root, _, files in os.walk(bot_dir):
                for p in ['main.py', 'bot.py', 'app.py', 'run.py']:
                    if p in files: ep = os.path.relpath(Path(root) / p, bot_dir); break
        else: dpath.rename(bot_dir / "user_bot.py")

        update_bot_entry(bid, ep); write_wrapper(bot_dir, ep)
        await msg.edit_text(f"✅ <b>Бот #{bid} развернут!</b>\n🚀 Точка входа: <code>{ep}</code>\n\nЗайди в «🤖 Мои боты» и нажми <b>▶️ Запуск</b>!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")]]), parse_mode="HTML")
    except Exception as e: await msg.edit_text(f"❌ Ошибка развертывания: {e}")
    await state.clear()

# ─── ОПЛАТА И СЛОТЫ ────────────────────────────────────────────

@dp.callback_query(F.data == "buy")
async def cb_buy(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if is_admin(call.from_user.id):
        return await call.message.edit_text("👑 <b>Тебе не нужно покупать слоты — у тебя безлимит!</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    text = "💎 <b>Выберите тарифный план:</b>\n\n━━━━━━━━━━━━━━━\nОплата производится подарком владельцу ⭐"
    kb = [
        [InlineKeyboardButton(text=f"📅 Неделя — {PLANS['week']['stars']}⭐", callback_data="plan:week")],
        [InlineKeyboardButton(text=f"🗓 2 недели — {PLANS['2weeks']['stars']}⭐", callback_data="plan:2weeks")],
        [InlineKeyboardButton(text=f"💎 Месяц — {PLANS['month']['stars']}⭐", callback_data="plan:month")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]
    ]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("plan:"))
async def cb_plan(call: types.CallbackQuery):
    pid = call.data.split(":")[1]; p = PLANS[pid]
    text = (f"{p['emoji']} <b>Тариф: {p['name']}</b>\n\n💎 <b>Стоимость:</b> {p['stars']}⭐\n📅 <b>Срок:</b> {p['days']} дней\n\n"
            f"━━━━━━━━━━━━━━━\n<b>Инструкция по оплате:</b>\n"
            f"1️⃣ Нажми «🎁 Отправить подарок»\n2️⃣ Отправь подарок владельцу на нужную сумму\n"
            f"3️⃣ Вернись и нажми «✅ Я оплатил»")
    kb = [
        [InlineKeyboardButton(text="🎁 Отправить подарок", url=get_profile_link())],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"pay_done:{pid}")],
        [InlineKeyboardButton(text="« Назад", callback_data="buy")]
    ]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("pay_done:"))
async def cb_pay_done(call: types.CallbackQuery):
    pid = call.data.split(":")[1]; p = PLANS[pid]; u = call.from_user
    if user_has_pending_request(u.id): return await call.answer("⏳ Твоя прошлая заявка ещё на проверке!", show_alert=True)
    rid = create_payment_request(u.id, u.username or "", u.full_name or "", pid)
    await call.message.edit_text(f"✅ <b>Заявка #{rid} создана!</b>\nЖди подтверждения администратором.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")
    try:
        kb_adm = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{rid}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{rid}")]])
        await bot.send_message(OWNER_ID, f"💰 <b>Заявка на оплату #{rid}</b>\n\n👤 @{u.username or '—'} (ID: <code>{u.id}</code>)\nТариф: <b>{p['name']}</b> ({p['stars']}⭐)", reply_markup=kb_adm, parse_mode="HTML")
    except: pass

@dp.callback_query(F.data == "myslots")
async def cb_myslots(call: types.CallbackQuery):
    if is_admin(call.from_user.id): return await call.message.edit_text("👑 <b>У тебя безлимитный доступ!</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")
    slots = get_active_slots(call.from_user.id)
    if not slots:
        return await call.message.edit_text("💳 <b>У тебя нет активных слотов.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить", callback_data="buy")],[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    text = f"📊 <b>Твои активные слоты ({len(slots)}):</b>\n\n"
    for s in slots:
        exp = datetime.fromisoformat(s[3])
        text += f"• <b>{PLANS.get(s[2], {}).get('name', s[2])}</b> — до {exp.strftime('%d.%m.%Y %H:%M')}\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить ещё", callback_data="buy")],[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

# ─── ПРОМОКОДЫ ДЛЯ ЮЗЕРА ──────────────────────────────────────

@dp.callback_query(F.data == "promo_enter")
async def cb_promo_enter(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.enter_promo)
    await call.message.edit_text("🎟 <b>Введи промокод:</b>\n\nОтправь его сообщением в чат или напиши /cancel", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="back_main")]]), parse_mode="HTML")

@dp.message(UserStates.enter_promo)
async def process_promo(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    ok, res = use_promo(message.from_user.id, code)
    if ok:
        p = PLANS[res]
        await message.answer(f"🎉 <b>Промокод активирован!</b>\n\nТебе зачислен тариф: <b>{p['name']}</b> ({p['days']} дней).", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],[InlineKeyboardButton(text="« В меню", callback_data="back_main")]]))
    else:
        await message.answer(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="back_main")]]))
    await state.clear()

# ─── УПРАВЛЕНИЕ БОТОМ И ИИ ────────────────────────────────────

@dp.callback_query(F.data == "mybots")
async def cb_mybots(call: types.CallbackQuery, state: FSMContext = None):
    if state: await state.clear()
    bots = get_user_bots(call.from_user.id)
    if not bots:
        return await call.message.edit_text("🤖 <b>У тебя пока нет загруженных ботов.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")],[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

    kb = []
    for b in bots:
        st = "🟢" if b[0] in running_bots else ("🧊" if b[6] else "🔴")
        kb.append([InlineKeyboardButton(text=f"{st} #{b[0]} • {b[2][:20]}", callback_data=f"bot:{b[0]}")])
    kb.append([InlineKeyboardButton(text="📤 Загрузить ещё", callback_data="upload")])
    kb.append([InlineKeyboardButton(text="« Меню", callback_data="back_main")])
    await call.message.edit_text(f"🤖 <b>Твои боты ({len(bots)}):</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("bot:"))
async def cb_bot_detail(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bid = int(call.data.split(":")[1]); b = get_bot(bid)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Доступ запрещен", show_alert=True)

    status = "🧊 Заморожен" if b[6] else ("🟢 Работает" if bid in running_bots else "🔴 Остановлен")
    kb = [
        [InlineKeyboardButton(text="▶️ Запуск", callback_data=f"start:{bid}"), InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stop:{bid}")],
        [InlineKeyboardButton(text="🔄 Перезапуск", callback_data=f"restart:{bid}"), InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bid}")],
        [InlineKeyboardButton(text="📁 Файлы", callback_data=f"files:{bid}"), InlineKeyboardButton(text="⚙️ Окружение (.env)", callback_data=f"envmenu:{bid}")],
        [InlineKeyboardButton(text="🧠 AI Поиск ошибки", callback_data=f"ai:{bid}")],
        [InlineKeyboardButton(text="🗑 Удалить бота", callback_data=f"del:{bid}")]
    ]
    if is_admin(call.from_user.id):
        kb.insert(0, [InlineKeyboardButton(text=f"👤 Владелец: ID {b[1]}", callback_data=f"adm_viewuser_id:{b[1]}")])
        if b[6]: kb.append([InlineKeyboardButton(text="♨️ Разморозить", callback_data=f"unfreeze:{bid}")])
        else: kb.append([InlineKeyboardButton(text="🧊 Заморозить", callback_data=f"freeze:{bid}")])

    kb.append([InlineKeyboardButton(text="« Назад", callback_data="mybots" if b[1] == call.from_user.id else "adm_allbots")])
    text = f"🤖 <b>Бот #{bid}</b>\n\n📁 Исходник: <code>{b[2]}</code>\n🚀 Точка входа: <code>{b[7]}</code>\n📊 Статус: <b>{status}</b>"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("start:"))
async def cb_start(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); b = get_bot(bid)
    if not b or b[6]: return await call.answer("🧊 Бот заморожен админом!", show_alert=True)
    await call.answer("⏳ Запуск...")
    if await start_user_bot(bid): await call.message.answer(f"✅ Бот #{bid} запущен!")
    else: await call.message.answer(f"❌ Ошибка запуска бота #{bid}.")

@dp.callback_query(F.data.startswith("stop:"))
async def cb_stop(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); await stop_user_bot(bid); await call.answer("⏹ Остановлен"); await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("restart:"))
async def cb_restart(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); await call.answer("🔄 Перезапуск..."); await stop_user_bot(bid); await asyncio.sleep(1); await start_user_bot(bid); await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("freeze:"))
async def cb_freeze(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    bid = int(call.data.split(":")[1]); freeze_bot(bid); await stop_user_bot(bid); await call.answer("🧊 Заморожен"); await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("unfreeze:"))
async def cb_unfreeze(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    bid = int(call.data.split(":")[1]); unfreeze_bot(bid); await call.answer("♨️ Разморожен"); await cb_bot_detail(call, None)

@dp.callback_query(F.data.startswith("envmenu:"))
async def cb_envmenu(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1])
    kb = [[InlineKeyboardButton(text="📝 Редактировать .env", callback_data=f"editenv:{bid}")],[InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bid}")]]
    await call.message.edit_text(f"⚙️ <b>Редактор окружения (.env) для бота #{bid}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("editenv:"))
async def cb_editenv(call: types.CallbackQuery, state: FSMContext):
    bid = int(call.data.split(":")[1]); env_p = BOTS_DIR / f"bot_{bid}" / ".env"
    curr = env_p.read_text(encoding="utf-8") if env_p.exists() else "# Пусто"
    await state.set_state(EnvStates.waiting_env_text); await state.update_data(target_bid=bid)
    await call.message.edit_text(f"📝 <b>Текущий .env:</b>\n<pre>{html.escape(curr)}</pre>\n\nОтправь новый текст в формате KEY=VALUE или /cancel", parse_mode="HTML")

@dp.message(EnvStates.waiting_env_text)
async def env_saved(message: types.Message, state: FSMContext):
    data = await state.get_data(); bid = data['target_bid']
    (BOTS_DIR / f"bot_{bid}" / ".env").write_text(message.text, encoding="utf-8")
    await message.answer("✅ <b>.env успешно сохранен!</b> Перезапусти бота.", parse_mode="HTML"); await state.clear()

@dp.callback_query(F.data.startswith("ai:"))
async def cb_ai(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); logs = get_bot_logs(bid, 80)
    if not logs: return await call.answer("📭 Логи пустые!", show_alert=True)
    msg = await call.message.answer("🧠 <i>ИИ анализирует ошибку...</i>", parse_mode="HTML")
    res = await analyze_with_groq(logs)
    await msg.edit_text(f"🧠 <b>Анализ нейросети:</b>\n\n{res}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bid}")]]))

@dp.callback_query(F.data.startswith("logs:"))
async def cb_logs(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); logs = get_bot_logs(bid, 40)
    text = f"📄 <b>Логи #{bid}</b>\n\n<pre>{html.escape(logs)}</pre>" if logs else "📭 Логи пустые"
    kb = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"logs:{bid}"), InlineKeyboardButton(text="🧠 AI Поиск ошибки", callback_data=f"ai:{bid}")],
        [InlineKeyboardButton(text="💾 Скачать log-файл", callback_data=f"downlog:{bid}")],
        [InlineKeyboardButton(text="« Назад", callback_data=f"bot:{bid}")]
    ]
    try: await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("downlog:"))
async def cb_downlog(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); lp = BOTS_DIR / f"bot_{bid}" / "bot.log"
    if lp.exists(): await call.message.answer_document(FSInputFile(str(lp), filename=f"bot_{bid}.log"))
    else: await call.answer("Лог пуст", show_alert=True)

@dp.callback_query(F.data.startswith("files:"))
async def cb_files(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); files = list_bot_files(bid)
    if not files:
        return await call.message.edit_text("📁 <b>Файлов нет.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Добавить файл", callback_data=f"addfile:{bid}")],[InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bid}")] Grac]), parse_mode="HTML")
    text = f"📁 <b>Файлы бота #{bid}:</b>\n\n"; kb = []
    for i, (fn, sz) in enumerate(files[:15]):
        text += f"• <code>{html.escape(fn)}</code> ({sz/1024:.1f} KB)\n"
        kb.append([InlineKeyboardButton(text=f"⬇️ {fn[:15]}", callback_data=f"getf:{bid}:{i}"), InlineKeyboardButton(text="🗑", callback_data=f"delf:{bid}:{i}")])
    kb.append([InlineKeyboardButton(text="➕ Добавить файл", callback_data=f"addfile:{bid}")])
    kb.append([InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bid}")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("addfile:"))
async def cb_addfile(call: types.CallbackQuery, state: FSMContext):
    bid = int(call.data.split(":")[1]); await state.set_state(AddFileStates.waiting_file); await state.update_data(target_bid=bid)
    await call.message.edit_text(f"➕ <b>Отправь файл или .zip архив для добавления в бота #{bid}:</b>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("getf:"))
async def cb_getf(call: types.CallbackQuery):
    _, bid, idx = call.data.split(":"); files = list_bot_files(int(bid))
    if int(idx) < len(files): await call.message.answer_document(FSInputFile(str(BOTS_DIR / f"bot_{bid}" / files[int(idx)][0])))
    await call.answer()

@dp.callback_query(F.data.startswith("delf:"))
async def cb_delf(call: types.CallbackQuery):
    _, bid, idx = call.data.split(":"); files = list_bot_files(int(bid))
    if int(idx) < len(files):
        fp = BOTS_DIR / f"bot_{bid}" / files[int(idx)][0]
        if fp.exists(): fp.unlink()
        await call.answer("🗑 Удалено"); await cb_files(call)

@dp.callback_query(F.data.startswith("del:"))
async def cb_delbot(call: types.CallbackQuery):
    bid = int(call.data.split(":")[1]); await stop_user_bot(bid)
    bd = BOTS_DIR / f"bot_{bid}"
    if bd.exists(): shutil.rmtree(bd, ignore_errors=True)
    delete_bot_record(bid); await call.answer("🗑 Удален"); await cb_mybots(call)

@dp.callback_query(F.data == "help")
async def cb_help(call: types.CallbackQuery):
    text = ("❓ <b>Помощь по хостингу BotHost:</b>\n\n"
            "1️⃣ <b>Как начать?</b>\nКупи слот или активируй промокод, затем отправь .py файл или .zip архив бота.\n\n"
            "2️⃣ <b>Поддерживает ли Discord ботов?</b>\nДа! Боты на Python (discord.py, disnake) работают отлично.\n\n"
            "3️⃣ <b>Как работает ИИ-дебаггер?</b>\nЗайди в своего бота -> Логи -> 🧠 AI Поиск ошибки.")
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Владелец", url=get_profile_link())],[InlineKeyboardButton(text="« Меню", callback_data="back_main")]]), parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
# 👑 ПАНЕЛЬ АДМИНА И GOD MODE
# ═══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery, state: FSMContext):
    if state: await state.clear()
    if not is_admin(call.from_user.id): return
    s = get_stats()
    pay_btn = "💰 Заявки 🔴" if s['pending'] > 0 else "💰 Заявки"
    text = (f"👑 <b>Панель Управления (God Mode)</b>\n\n"
            f"👥 Юзеров: <b>{s['users']}</b> | 🚫 Бан: <b>{s['banned']}</b>\n"
            f"🛡 Админов: <b>{s['admins']}</b> | 💳 Слотов: <b>{s['slots']}</b>\n"
            f"🤖 Ботов: <b>{s['bots']}</b> (🟢 <b>{s['running']}</b> | 🧊 <b>{s['frozen']}</b>)\n"
            f"💰 Ожидают оплаты: <b>{s['pending']}</b>\n"
            f"⏱ Uptime: <b>{get_uptime()}</b>")

    kb = [
        [InlineKeyboardButton(text=pay_btn, callback_data="adm_payments"), InlineKeyboardButton(text="🎟 Промокоды", callback_data="adm_promos")],
        [InlineKeyboardButton(text="🤖 Все боты (God Mode)", callback_data="adm_allbots")],
        [InlineKeyboardButton(text="✉️ Написать юзеру в ЛС", callback_data="adm_msguser"), InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="adm_ban"), InlineKeyboardButton(text="✅ Разбанить", callback_data="adm_unban")],
        [InlineKeyboardButton(text="🛡 +Админ", callback_data="adm_addadmin"), InlineKeyboardButton(text="❌ -Админ", callback_data="adm_remadmin")],
        [InlineKeyboardButton(text="💾 Скачать БД", callback_data="adm_backup"), InlineKeyboardButton(text="🔄 Рестарт ВСЕХ", callback_data="adm_restart_all")],
        [InlineKeyboardButton(text="« В главное меню", callback_data="back_main")]
    ]
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data == "adm_payments")
async def cb_adm_payments(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    reqs = get_pending_requests()
    if not reqs: return await call.message.edit_text("💰 <b>Нет новых заявок на оплату.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Админка", callback_data="admin")]]), parse_mode="HTML")
    text = f"💰 <b>Ожидают проверки ({len(reqs)}):</b>\n\n"
    kb = []
    for r in reqs:
        p = PLANS.get(r[4], {})
        text += f"Заявка #{r[0]} | Юзер: @{r[2]} (<code>{r[1]}</code>) | Тариф: {p.get('name', r[4])}\n"
        kb.append([InlineKeyboardButton(text=f"✅ #{r[0]}", callback_data=f"approve:{r[0]}"), InlineKeyboardButton(text=f"❌ #{r[0]}", callback_data=f"reject:{r[0]}")])
    kb.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split(":")[1]); req = get_payment_request(rid)
    if not req or req[5] != "pending": return await call.answer("Уже обработано", show_alert=True)
    approve_payment(rid); create_slot(req[1], req[4])
    await call.message.edit_text(f"✅ <b>Заявка #{rid} одобрена!</b> Слот выдан.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="adm_payments")]]), parse_mode="HTML")
    try: await bot.send_message(req[1], "🎉 <b>Твоя оплата подтверждена!</b> Можно загружать бота.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")]]), parse_mode="HTML")
    except: pass

@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split(":")[1]); req = get_payment_request(rid)
    if not req or req[5] != "pending": return await call.answer("Уже обработано", show_alert=True)
    reject_payment(rid)
    await call.message.edit_text(f"❌ <b>Заявка #{rid} отклонена.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="adm_payments")]]), parse_mode="HTML")
    try: await bot.send_message(req[1], "❌ <b>Заявка на оплату была отклонена.</b> Напиши владельцу, если это ошибка.", parse_mode="HTML")
    except: pass

@dp.callback_query(F.data == "adm_promos")
async def cb_adm_promos(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    promos = get_all_promos()
    text = "🎟 <b>Активные промокоды:</b>\n\n"; kb = [[InlineKeyboardButton(text="➕ Создать промокод", callback_data="adm_promo_add")]]
    if not promos: text += "Промокодов пока нет."
    else:
        for p in promos:
            text += f"• <code>{p[1]}</code> — {PLANS.get(p[2], {}).get('name', p[2])} (Осталось: {p[3]})\n"
            kb.append([InlineKeyboardButton(text=f"❌ Удалить {p[1]}", callback_data=f"adm_promo_del:{p[0]}")])
    kb.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data == "adm_promo_add")
async def cb_adm_promo_add(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.promo_code)
    await call.message.edit_text("🎟 <b>Отправь код промокода (на латинице):</b>", parse_mode="HTML")

@dp.message(AdminStates.promo_code)
async def adm_promo_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper(); await state.update_data(code=code)
    kb = [
        [InlineKeyboardButton(text="📅 Неделя", callback_data="adm_plan:week")],
        [InlineKeyboardButton(text="🗓 2 недели", callback_data="adm_plan:2weeks")],
        [InlineKeyboardButton(text="💎 Месяц", callback_data="adm_plan:month")]
    ]
    await message.answer(f"Промокод: <code>{code}</code>\nВыбери тариф:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_plan:"))
async def adm_promo_plan(call: types.CallbackQuery, state: FSMContext):
    plan = call.data.split(":")[1]; await state.update_data(plan=plan)
    await state.set_state(AdminStates.promo_uses)
    await call.message.edit_text("Отправь количество активаций (числом):")

@dp.message(AdminStates.promo_uses)
async def adm_promo_uses(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Нужна цифра!")
    data = await state.get_data(); create_promo(data['code'], data['plan'], int(message.text))
    await message.answer(f"✅ Промокод <code>{data['code']}</code> создан!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« К промокодам", callback_data="adm_promos")]]), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data.startswith("adm_promo_del:"))
async def cb_adm_promo_del(call: types.CallbackQuery):
    delete_promo(int(call.data.split(":")[1])); await call.answer("🗑 Удалено"); await cb_adm_promos(call)

@dp.callback_query(F.data == "adm_allbots")
async def cb_adm_allbots(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    bots = get_all_bots(); kb = []
    for b in bots[-30:]:
        st = "🟢" if b[0] in running_bots else ("🧊" if b[6] else "🔴")
        kb.append([InlineKeyboardButton(text=f"{st} #{b[0]} (Юзер: {b[1]}) • {b[2][:15]}", callback_data=f"bot:{b[0]}")])
    kb.append([InlineKeyboardButton(text="« Админка", callback_data="admin")])
    await call.message.edit_text("🤖 <b>Все боты на хостинге (God Mode):</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_viewuser_id:"))
async def cb_adm_viewuser_id(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.split(":")[1]); u = get_user(uid)
    if not u: return await call.answer("Не найден в БД", show_alert=True)
    text = f"👤 <b>Информация о юзере:</b>\n\nID: <code>{u[0]}</code>\nUsername: @{u[1] or '—'}\nЗабанен: {'Да' if u[4] else 'Нет'}"
    kb = [[InlineKeyboardButton(text="🚫 Забанить" if not u[4] else "✅ Разбанить", callback_data=f"adm_act_toggleban:{u[0]}")],[InlineKeyboardButton(text="« Назад", callback_data="admin")]]
    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_act_toggleban:"))
async def cb_adm_toggleban(call: types.CallbackQuery):
    uid = int(call.data.split(":")[1]); u = get_user(uid)
    if u[4]: unban_user(uid)
    else:
        ban_user(uid)
        for b in get_user_bots(uid): await stop_user_bot(b[0])
    await call.answer("Готово!"); await cb_admin(call, None)

@dp.callback_query(F.data == "adm_msguser")
async def cb_adm_msguser(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.msg_uid)
    await call.message.edit_text("✉️ <b>Введи ID или @username юзера:</b>", parse_mode="HTML")

@dp.message(AdminStates.msg_uid)
async def adm_msg_uid(message: types.Message, state: FSMContext):
    txt = message.text.strip(); uid = find_user_by_username(txt) if txt.startswith("@") else (int(txt) if txt.isdigit() else None)
    if not uid: return await message.answer("❌ Юзер не найден!")
    await state.update_data(target_uid=uid); await state.set_state(AdminStates.msg_text)
    await message.answer(f"Напиши сообщение для <code>{uid}</code>:", parse_mode="HTML")

@dp.message(AdminStates.msg_text)
async def adm_msg_send(message: types.Message, state: FSMContext):
    data = await state.get_data(); uid = data['target_uid']
    try:
        await bot.send_message(uid, f"✉️ <b>Сообщение от администрации:</b>\n\n{message.text}", parse_mode="HTML")
        await message.answer("✅ Отправлено!")
    except Exception as e: await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@dp.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text("📢 <b>Отправь текст для общей рассылки:</b>", parse_mode="HTML")

@dp.message(AdminStates.broadcast)
async def adm_broadcast_send(message: types.Message, state: FSMContext):
    await state.clear(); users = get_all_users(); ok = 0
    msg = await message.answer(f"⏳ Рассылка для {len(users)} юзеров...")
    for u in users:
        try:
            await bot.send_message(u[0], message.html_text or message.text, parse_mode="HTML")
            ok += 1; await asyncio.sleep(0.05)
        except: pass
    await msg.edit_text(f"✅ <b>Рассылка завершена!</b> Доставлено: {ok}/{len(users)}", parse_mode="HTML")

@dp.callback_query(F.data == "adm_ban")
async def cb_adm_ban(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.ban); await call.message.edit_text("🚫 Введи ID или @username для бана:")

@dp.message(AdminStates.ban)
async def adm_ban_do(message: types.Message, state: FSMContext):
    txt = message.text.strip(); uid = find_user_by_username(txt) if txt.startswith("@") else (int(txt) if txt.isdigit() else None)
    if uid:
        ban_user(uid)
        for b in get_user_bots(uid): await stop_user_bot(b[0])
        await message.answer(f"🚫 <code>{uid}</code> забанен!")
    await state.clear()

@dp.callback_query(F.data == "adm_unban")
async def cb_adm_unban(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.unban); await call.message.edit_text("✅ Введи ID для разбана:")

@dp.message(AdminStates.unban)
async def adm_unban_do(message: types.Message, state: FSMContext):
    if message.text.isdigit(): unban_user(int(message.text)); await message.answer("✅ Разбанен!")
    await state.clear()

@dp.callback_query(F.data == "adm_addadmin")
async def cb_adm_addadmin(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID: return
    await state.set_state(AdminStates.addadmin); await call.message.edit_text("🛡 Введи ID нового админа:")

@dp.message(AdminStates.addadmin)
async def adm_addadmin_do(message: types.Message, state: FSMContext):
    if message.text.isdigit(): add_admin(int(message.text)); await message.answer("🛡 Админ добавлен!")
    await state.clear()

@dp.callback_query(F.data == "adm_remadmin")
async def cb_adm_remadmin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return
    admins = get_all_admins()
    kb = [[InlineKeyboardButton(text=f"❌ {a[1] or a[0]}", callback_data=f"remadm:{a[0]}")] for a in admins]
    kb.append([InlineKeyboardButton(text="« Отмена", callback_data="admin")])
    await call.message.edit_text("Удалить админа:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("remadm:"))
async def cb_remadm_do(call: types.CallbackQuery):
    remove_admin(int(call.data.split(":")[1])); await call.answer("Удален"); await cb_admin(call, None)

@dp.callback_query(F.data == "adm_backup")
async def cb_adm_backup(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return
    if os.path.exists(DB_PATH): await call.message.answer_document(FSInputFile(DB_PATH, filename="bot_backup.db"))
    await call.answer()

@dp.callback_query(F.data == "adm_restart_all")
async def cb_restart_all(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer("⏳ Рестарт всех ботов...")
    for bid in list(running_bots.keys()): await stop_user_bot(bid)
    restarted = 0
    for b in get_all_bots():
        if b[6] == 0 and not is_user_banned(b[1]):
            if await start_user_bot(b[0]): restarted += 1
    await call.message.answer(f"🔄 Перезапущено активных ботов: {restarted}")

@dp.callback_query(F.data == "back_main")
async def back_main(call: types.CallbackQuery, state: FSMContext):
    if state: await state.clear()
    await call.message.edit_text(f"✨ <b>BotHost v6.0 AI</b>", reply_markup=main_menu_kb(call.from_user.id), parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
# 🎯 ГЛАВНЫЙ ЗАПУСК СЕРВЕРА
# ═══════════════════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("=" * 50)
    logger.info("🤖 BotHost v6.0 Ultimate Успешно Запущен!")
    logger.info(f"👤 Владелец: {OWNER_ID}")
    logger.info("=" * 50)

    # Восстановление ботов и фоновые процессы
    await restore_running_bots()
    asyncio.create_task(monitor_bots())
    asyncio.create_task(auto_backup())

    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("👋 Выход")
