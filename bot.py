"""
🤖 BotHost — хостинг Telegram-ботов (v2.0 для Railway)
✅ Автоустановка pip-библиотек
✅ Persistent Volume для данных
✅ Стабильный wrapper без синтаксических ошибок
✅ Все FSM работают
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

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_TELEGRAM_ID"])
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "ivan_unreal")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
BOTS_DIR = DATA_DIR / "bots"
DB_PATH = DATA_DIR / "bot.db"
WELCOME_IMAGE = DATA_DIR / "welcome.jpg"

PLANS = {
    "week":   {"name": "Неделя",    "stars": 15, "days": 7,  "emoji": "📅"},
    "2weeks": {"name": "2 недели",  "stars": 25, "days": 14, "emoji": "📅"},
    "month":  {"name": "Месяц",     "stars": 50, "days": 30, "emoji": "🗓"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S"
)
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
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT,
        expires_at TEXT, created_at TEXT, gift_id TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT,
        bot_token TEXT, status TEXT DEFAULT 'stopped', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS pending_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        gift_value INTEGER, gift_id TEXT UNIQUE, status TEXT DEFAULT 'pending',
        plan TEXT, created_at TEXT)""")
    conn.commit()
    conn.close()
    logger.info(f"💾 БД инициализирована: {DB_PATH}")


def get_db():
    return sqlite3.connect(DB_PATH)


# ─── Пользователи ─────────────────────────────────────────

def create_user(user_id, username, full_name=""):
    conn = get_db(); c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET username = ?, full_name = ?",
        (user_id, username, full_name, datetime.now().isoformat(), username, full_name)
    )
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
    c.execute("INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
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
    c.execute("SELECT COUNT(*) FROM slots WHERE user_id = ? AND expires_at > ?",
              (user_id, datetime.now().isoformat()))
    count = c.fetchone()[0]; conn.close()
    return count > 0


def get_active_slots(user_id):
    if user_id == OWNER_ID:
        return [(0, OWNER_ID, "owner", "2099-12-31", datetime.now().isoformat(), "owner")]
    if is_admin(user_id):
        return [(0, user_id, "admin", "2099-12-31", datetime.now().isoformat(), "admin")]
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM slots WHERE user_id = ? AND expires_at > ?",
              (user_id, datetime.now().isoformat()))
    rows = c.fetchall(); conn.close()
    return rows


def create_slot(user_id, plan, gift_id=""):
    days = PLANS[plan]["days"]
    expires_at = datetime.now() + timedelta(days=days)
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO slots (user_id, plan, expires_at, created_at, gift_id) VALUES (?, ?, ?, ?, ?)",
              (user_id, plan, expires_at.isoformat(), datetime.now().isoformat(), gift_id))
    conn.commit(); conn.close()


def save_bot(user_id, filename, user_bot_token):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO bots (user_id, filename, bot_token, created_at) VALUES (?, ?, ?, ?)",
              (user_id, filename, user_bot_token, datetime.now().isoformat()))
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


def save_pending_gift(user_id, username, gift_value, gift_id):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO pending_gifts (user_id, username, gift_value, gift_id, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, gift_value, gift_id, datetime.now().isoformat()))
        conn.commit(); success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success


def get_pending_gift_for_plan(user_id, plan):
    required = PLANS[plan]["stars"]
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, gift_value, gift_id FROM pending_gifts 
                 WHERE user_id = ? AND status = 'pending' AND gift_value >= ?
                 ORDER BY created_at DESC LIMIT 1""", (user_id, required))
    row = c.fetchone(); conn.close()
    return row


def activate_gift(gift_db_id, plan):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE pending_gifts SET status = 'activated', plan = ? WHERE id = ?", (plan, gift_db_id))
    conn.commit(); conn.close()


def get_stats():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1"); banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1"); admins = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM slots WHERE expires_at > ?", (datetime.now().isoformat(),))
    active_slots = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM bots"); total_bots = c.fetchone()[0]
    c.execute("SELECT COUNT(*), COALESCE(SUM(gift_value), 0) FROM pending_gifts WHERE status = 'activated'")
    gifts_row = c.fetchone()
    conn.close()
    return {
        "total_users": total_users, "banned": banned, "admins": admins,
        "active_slots": active_slots, "total_bots": total_bots,
        "running_bots": len(running_bots),
        "total_gifts": gifts_row[0], "total_stars": gifts_row[1],
    }


# ═══════════════════════════════════════════════════════════════
# 🚀 WRAPPER для запуска ботов (ИСПРАВЛЕННЫЙ)
# ═══════════════════════════════════════════════════════════════

WRAPPER_CODE = '''#!/usr/bin/env python3
"""Wrapper для запуска пользовательского бота с автоустановкой библиотек"""
import os
import sys
import re
import signal
import subprocess
import traceback

def log(msg):
    print(f"[BotHost] {msg}", flush=True)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

if BOT_TOKEN:
    log(f"Токен: {BOT_TOKEN[:10]}...")
else:
    log("Запуск БЕЗ токена")

log(f"Python: {sys.version.split()[0]}")

if not os.path.exists("user_bot.py"):
    log("ERROR: user_bot.py не найден!")
    sys.exit(1)

with open("user_bot.py", "r", encoding="utf-8") as f:
    user_code = f.read()

log(f"Прочитано: {len(user_code)} символов")

# Автоматическая установка недостающих библиотек
STDLIB_MODULES = {
    "os", "sys", "re", "json", "time", "datetime", "asyncio", "logging",
    "pathlib", "typing", "subprocess", "signal", "html", "math", "random",
    "collections", "itertools", "functools", "traceback", "threading",
    "queue", "socket", "urllib", "http", "email", "base64", "hashlib",
    "hmac", "uuid", "sqlite3", "csv", "io", "tempfile", "shutil", "copy",
    "argparse", "warnings", "contextlib", "dataclasses", "enum", "abc",
    "inspect", "operator", "string", "textwrap", "unicodedata", "struct",
    "codecs", "pickle", "gzip", "zipfile", "tarfile", "glob", "fnmatch",
    "__future__", "builtins", "gc", "atexit", "weakref", "types", "decimal",
    "fractions", "statistics", "secrets", "ssl", "ftplib", "smtplib",
    "imaplib", "poplib", "concurrent", "multiprocessing", "pprint", "difflib",
    "getpass", "platform", "locale", "gettext", "calendar",
}

# Маппинг имени импорта -> имя пакета в pip
PIP_MAPPING = {
    "telebot": "pyTelegramBotAPI",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "telegram": "python-telegram-bot",
    "google": "google-api-python-client",
    "discord": "discord.py",
    "attr": "attrs",
    "OpenSSL": "pyOpenSSL",
    "serial": "pyserial",
    "magic": "python-magic",
    "jose": "python-jose",
    "jwt": "PyJWT",
    "MySQLdb": "mysqlclient",
    "psycopg2": "psycopg2-binary",
}

def find_imports(code):
    """Извлечь все top-level импорты"""
    imports = set()
    for line in code.split("\\n"):
        line = line.strip()
        # import X, import X.Y, import X as Y
        m = re.match(r"^import\\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
        if m:
            imports.add(m.group(1))
            continue
        # from X import Y, from X.Y import Z
        m = re.match(r"^from\\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
        if m:
            imports.add(m.group(1))
    return imports

def is_installed(module_name):
    """Проверка установлен ли модуль"""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False
    except Exception:
        return True  # если импорт даёт другую ошибку — считаем установленным

def pip_install(package):
    """Установка пакета через pip"""
    try:
        log(f"📦 Устанавливаю: {package}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir", package],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log(f"✅ Установлено: {package}")
            return True
        else:
            log(f"❌ Ошибка установки {package}: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"⏱ Таймаут установки {package}")
        return False
    except Exception as e:
        log(f"❌ Исключение при установке {package}: {e}")
        return False

log("🔍 Анализ зависимостей...")
imports = find_imports(user_code)
missing = []
for imp in imports:
    if imp in STDLIB_MODULES:
        continue
    if is_installed(imp):
        continue
    missing.append(imp)

if missing:
    log(f"📦 Нужно установить: {missing}")
    for module in missing:
        package = PIP_MAPPING.get(module, module)
        pip_install(package)
else:
    log("✅ Все зависимости на месте")

# Обработчик сигналов
def handle_signal(signum, frame):
    log(f"Сигнал {signum}, завершаюсь...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

log("🚀 Запускаю код пользователя...")
sys.stdout.flush()

try:
    globals_dict = {
        "__name__": "__main__",
        "__file__": os.path.abspath("user_bot.py"),
        "__builtins__": __builtins__,
    }
    code_obj = compile(user_code, "user_bot.py", "exec")
    exec(code_obj, globals_dict)
    log("✅ Код выполнен")
except SystemExit as e:
    code = e.code if e.code is not None else 0
    log(f"Завершение с кодом: {code}")
    sys.exit(code)
except SyntaxError as e:
    log(f"❌ SYNTAX ERROR: {e.filename}:{e.lineno}")
    log(f"   {e.msg}")
    if e.text:
        log(f"   >>> {e.text.strip()}")
    sys.exit(1)
except ImportError as e:
    log(f"❌ IMPORT ERROR: {e}")
    log("Пробую установить и перезапуститься...")
    module_match = re.search(r"'([^']+)'", str(e))
    if module_match:
        mod = module_match.group(1).split(".")[0]
        pkg = PIP_MAPPING.get(mod, mod)
        if pip_install(pkg):
            log("Установлено. Перезапусти бота!")
    traceback.print_exc()
    sys.exit(1)
except KeyboardInterrupt:
    log("Прервано")
    sys.exit(0)
except Exception as e:
    log(f"❌ ОШИБКА: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
'''


async def start_user_bot(bot_id: int, code: str, user_bot_token: str) -> bool:
    try:
        bot_dir = BOTS_DIR / f"bot_{bot_id}"
        bot_dir.mkdir(exist_ok=True)

        (bot_dir / "user_bot.py").write_text(code, encoding="utf-8")
        (bot_dir / "wrapper.py").write_text(WRAPPER_CODE, encoding="utf-8")

        log_file = bot_dir / "bot.log"

        env = os.environ.copy()
        if user_bot_token:
            env["BOT_TOKEN"] = user_bot_token
        else:
            env.pop("BOT_TOKEN", None)
        env["PYTHONUNBUFFERED"] = "1"

        # Убираем секретные переменные владельца
        for k in ["OWNER_TELEGRAM_ID", "OWNER_PHONE", "OWNER_API_ID",
                  "OWNER_API_HASH", "OWNER_USERNAME"]:
            env.pop(k, None)

        with open(log_file, "w", encoding="utf-8") as lf:
            process = subprocess.Popen(
                [sys.executable, "-u", "wrapper.py"],
                cwd=str(bot_dir),
                env=env,
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )

        running_bots[bot_id] = process

        # Ждём инициализации (с учётом возможной установки библиотек)
        await asyncio.sleep(8)

        if process.poll() is not None:
            # Если бот использует pip install — подождём ещё
            await asyncio.sleep(4)
            if process.poll() is not None:
                logs = log_file.read_text(encoding="utf-8", errors="ignore")
                logger.error(f"❌ Бот #{bot_id} упал:\n{logs[-1000:]}")
                conn = get_db(); c = conn.cursor()
                c.execute("UPDATE bots SET status = 'error' WHERE id = ?", (bot_id,))
                conn.commit(); conn.close()
                if bot_id in running_bots:
                    del running_bots[bot_id]
                return False

        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE bots SET status = 'running' WHERE id = ?", (bot_id,))
        conn.commit(); conn.close()

        logger.info(f"✅ Бот #{bot_id} запущен (PID {process.pid})")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка запуска #{bot_id}: {e}")
        return False


async def stop_user_bot(bot_id: int):
    if bot_id in running_bots:
        proc = running_bots[bot_id]
        try:
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except Exception as e:
            logger.error(f"Ошибка остановки #{bot_id}: {e}")
        finally:
            if bot_id in running_bots:
                del running_bots[bot_id]

    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
    conn.commit(); conn.close()
    logger.info(f"⏹ Бот #{bot_id} остановлен")


def get_bot_logs(bot_id: int, lines: int = 50) -> str:
    log_file = BOTS_DIR / f"bot_{bot_id}" / "bot.log"
    if not log_file.exists():
        return "📭 Логи пустые"
    try:
        content = log_file.read_text(encoding="utf-8", errors="ignore")
        log_lines = content.strip().split("\n")
        return "\n".join(log_lines[-lines:]) or "📭 Логи пустые"
    except Exception as e:
        return f"❌ Ошибка: {e}"


async def monitor_bots():
    logger.info("🔄 Мониторинг запущен")
    while True:
        try:
            for bot_id, proc in list(running_bots.items()):
                if proc.poll() is not None:
                    code = proc.returncode
                    del running_bots[bot_id]
                    conn = get_db(); c = conn.cursor()
                    c.execute("UPDATE bots SET status = 'error' WHERE id = ?", (bot_id,))
                    c.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
                    row = c.fetchone()
                    conn.commit(); conn.close()

                    if row and row[0] != OWNER_ID:
                        logs = get_bot_logs(bot_id, 10)
                        logs_safe = html.escape(logs[-500:])
                        try:
                            await bot.send_message(
                                row[0],
                                f"⚠️ <b>Бот #{bot_id} упал</b>\n\n"
                                f"Код: {code}\n<pre>{logs_safe}</pre>",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Уведомление: {e}")
                else:
                    conn = get_db(); c = conn.cursor()
                    c.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
                    row = c.fetchone(); conn.close()
                    if row:
                        uid = row[0]
                        if uid != OWNER_ID and not is_admin(uid):
                            if is_user_banned(uid) or not has_active_slot(uid):
                                await stop_user_bot(bot_id)
        except Exception as e:
            logger.error(f"Мониторинг: {e}")
        await asyncio.sleep(30)


async def restore_running_bots():
    logger.info("🔄 Восстановление ботов...")
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, user_id, bot_token, status FROM bots WHERE status = 'running'")
    bots_to_restore = c.fetchall()
    conn.close()

    restored = 0
    for bot_id, user_id, user_bot_token, status in bots_to_restore:
        if is_user_banned(user_id): continue
        if user_id != OWNER_ID and not is_admin(user_id) and not has_active_slot(user_id):
            continue
        code_file = BOTS_DIR / f"bot_{bot_id}" / "user_bot.py"
        if code_file.exists():
            code = code_file.read_text(encoding="utf-8")
            if await start_user_bot(bot_id, code, user_bot_token or ""):
                restored += 1
    logger.info(f"✅ Восстановлено: {restored}")


# ═══════════════════════════════════════════════════════════════
# 🎁 ПОДАРКИ
# ═══════════════════════════════════════════════════════════════

async def check_gifts():
    if not all([OWNER_PHONE, OWNER_API_ID, OWNER_API_HASH]):
        logger.warning("⚠️ Подарки отключены (нет OWNER_PHONE/API_ID/API_HASH)")
        return
    try:
        from telethon import TelegramClient, events
        session_path = str(DATA_DIR / "owner_session")
        client = TelegramClient(session_path, int(OWNER_API_ID), OWNER_API_HASH)
        await client.start(phone=OWNER_PHONE)
        logger.info(f"✅ Userbot подключен")

        @client.on(events.NewMessage(incoming=True))
        async def on_msg(event):
            try:
                if hasattr(event.message, 'action'):
                    action = event.message.action
                    if 'gift' in str(type(action)).lower():
                        sender = await event.get_sender()
                        if sender and sender.id != OWNER_ID:
                            value = getattr(action, 'stars', 0) or getattr(action, 'cost', 0) or 0
                            gift_id = f"{event.id}_{event.chat_id}_{int(datetime.now().timestamp())}"
                            await register_gift(sender.id, sender.username or sender.first_name, value, gift_id)
            except Exception as e:
                logger.error(f"Подарок: {e}")

        await client.run_until_disconnected()
    except ImportError:
        logger.warning("Telethon не установлен")
    except Exception as e:
        logger.error(f"Userbot: {e}")


async def register_gift(user_id, username, value, gift_id):
    if not save_pending_gift(user_id, username, value, gift_id): return

    plan_name = None
    if value >= 50: plan_name = "Месяц"
    elif value >= 25: plan_name = "2 недели"
    elif value >= 15: plan_name = "Неделя"

    try:
        if plan_name:
            await bot.send_message(user_id,
                f"🎁 <b>Подарок получен!</b>\n\n💎 {value}⭐\n\n"
                f"✅ Вернись в бота, нажми <b>«💎 Купить слот»</b>, "
                f"выбери <b>{plan_name}</b> и <b>«✅ Я отправил подарок»</b>",
                parse_mode="HTML")
        else:
            await bot.send_message(user_id, f"🎁 Спасибо ({value}⭐), но минимум 15⭐")
    except Exception as e:
        logger.error(f"Не уведомил {user_id}: {e}")

    try:
        await bot.send_message(OWNER_ID,
            f"🎁 <b>Подарок!</b>\n@{username or '—'} (<code>{user_id}</code>) — {value}⭐",
            parse_mode="HTML")
    except: pass
    logger.info(f"🎁 {user_id} → {value}⭐")


# ═══════════════════════════════════════════════════════════════
# 💬 ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════════

def get_profile_link():
    return f"https://t.me/{OWNER_USERNAME}" if OWNER_USERNAME else f"tg://user?id={OWNER_ID}"


WELCOME_TEXT = """👋 <b>Привет, {name}!</b>

Я — <b>BotHost</b>, хостинг для Telegram-ботов.

━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>Как начать?</b>
1️⃣ Нажми «💎 Купить слот»
2️⃣ Выбери тариф
3️⃣ Отправь подарок владельцу
4️⃣ Подтверди оплату
5️⃣ Загрузи своего бота ✨

━━━━━━━━━━━━━━━━━━━━━━━

Выбери действие ниже 👇"""


def main_menu_kb(user_id):
    buttons = [
        [InlineKeyboardButton(text="💎 Купить слот", callback_data="buy")],
        [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
        [InlineKeyboardButton(text="🤖 Мои боты", callback_data="mybots")],
        [InlineKeyboardButton(text="📊 Мои слоты", callback_data="myslots")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ]
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_welcome(target, edit=False):
    user_id = target.from_user.id if hasattr(target, 'from_user') else target.chat.id
    name = target.from_user.first_name if hasattr(target, 'from_user') else "друг"
    text = WELCOME_TEXT.format(name=name)
    kb = main_menu_kb(user_id)
    chat_id = target.chat.id if hasattr(target, 'chat') else user_id

    if WELCOME_IMAGE.exists() and user_id != OWNER_ID:
        try:
            if edit:
                try: await target.delete()
                except: pass
            photo = FSInputFile(WELCOME_IMAGE)
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=text,
                                 reply_markup=kb, parse_mode="HTML")
            return
        except Exception as e:
            logger.error(f"Ошибка фото: {e}")

    if edit:
        try:
            await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
            return
        except: pass

    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Приветствие: {e}")


# ═══════════════════════════════════════════════════════════════
# 📝 FSM
# ═══════════════════════════════════════════════════════════════

class UploadStates(StatesGroup):
    waiting_file = State()
    waiting_token = State()


class AdminStates(StatesGroup):
    broadcast = State()
    ban = State()
    unban = State()
    addadmin = State()
    welcome_photo = State()


# ═══════════════════════════════════════════════════════════════
# 📱 ХЕНДЛЕРЫ
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 <b>Вы заблокированы</b>", parse_mode="HTML")
        return
    create_user(message.from_user.id, message.from_user.username or "",
                message.from_user.full_name or "")
    await send_welcome(message)


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено")


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id): return
    await show_admin_panel(message)


# ─── FSM: Рассылка ────────────────────────────────────────

@dp.message(AdminStates.broadcast)
async def handle_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear(); return
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("❌ Отменено")
    text = message.text or message.caption or ""
    if not text: return

    await message.answer("⏳ Рассылаю...")
    ok, fail = 0, 0
    for u in get_all_users():
        if u[4]: continue
        try:
            await bot.send_message(u[0], text)
            ok += 1
            await asyncio.sleep(0.05)
        except: fail += 1

    await message.answer(f"✅ Готово!\n✓ Доставлено: {ok}\n✗ Ошибок: {fail}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]))
    await state.clear()


@dp.message(AdminStates.ban)
async def handle_ban(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear(); return
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("❌ Отменено")

    text = message.text.strip()
    if text.startswith("@"):
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (text[1:],))
        row = c.fetchone(); conn.close()
        if not row: return await message.answer("❌ Не найден")
        uid = row[0]
    else:
        try: uid = int(text)
        except: return await message.answer("❌ Неверный формат")

    if uid == OWNER_ID: return await message.answer("❌ Нельзя")

    ban_user(uid)
    for b in get_user_bots(uid):
        await stop_user_bot(b[0])

    await message.answer(f"🚫 <b>Заблокирован:</b> <code>{uid}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")
    await state.clear()


@dp.message(AdminStates.unban)
async def handle_unban(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear(); return
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("❌ Отменено")
    try: uid = int(message.text.strip())
    except: return await message.answer("❌ Неверный ID")

    unban_user(uid)
    await message.answer(f"✅ <b>Разблокирован:</b> <code>{uid}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")
    await state.clear()


@dp.message(AdminStates.addadmin)
async def handle_addadmin(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        await state.clear(); return
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("❌ Отменено")

    text = message.text.strip()
    if text.startswith("@"):
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (text[1:],))
        row = c.fetchone(); conn.close()
        if not row: return await message.answer("❌ Не найден. Пусть напишет /start")
        uid = row[0]
    else:
        try: uid = int(text)
        except: return await message.answer("❌ Неверный формат")

    if uid == OWNER_ID: return await message.answer("⚠️ Уже владелец")

    add_admin(uid)
    await message.answer(f"🛡 <b>Админ добавлен:</b> <code>{uid}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")
    await state.clear()


@dp.message(AdminStates.welcome_photo, F.photo)
async def handle_welcome_photo(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        await state.clear(); return
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, WELCOME_IMAGE)
    await message.answer("✅ <b>Картинка установлена!</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")
    await state.clear()


@dp.message(AdminStates.welcome_photo, F.text)
async def handle_welcome_text(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        await state.clear(); return
    if message.text.strip().lower() == "delete":
        if WELCOME_IMAGE.exists():
            WELCOME_IMAGE.unlink()
            await message.answer("🗑 <b>Удалена</b>", parse_mode="HTML")
        else:
            await message.answer("📭 Нет картинки")
        await state.clear()
    elif message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
    else:
        await message.answer("❌ Отправь фото или 'delete'")


# ─── FSM: Загрузка ────────────────────────────────────────

@dp.message(UploadStates.waiting_file, F.document)
async def handle_file(message: types.Message, state: FSMContext):
    doc = message.document
    if not (doc.file_name.endswith(".py") or doc.file_name.endswith(".txt")):
        return await message.answer("❌ Нужен <b>.py-файл</b>", parse_mode="HTML")
    if doc.file_size and doc.file_size > 500 * 1024:
        return await message.answer("❌ Больше 500 КБ")

    file_info = await bot.get_file(doc.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    code = file_bytes.read().decode("utf-8", errors="ignore")

    if not code.strip():
        return await message.answer("❌ Файл пустой!")

    warnings = []
    tg_libs = ["aiogram", "telebot", "pyrogram", "telegram", "telethon"]
    if not any(lib in code.lower() for lib in tg_libs):
        warnings.append("💡 Не найдено Telegram-библиотек")
    if re.search(r'\d{8,10}:[A-Za-z0-9_-]{35}', code):
        warnings.append("⚠️ Хардкоднутый токен — лучше os.environ.get('BOT_TOKEN')")

    await state.update_data(code=code, filename=doc.file_name)

    response = f"✅ <b>Файл принят!</b>\n\n📁 {doc.file_name}\n📏 {len(code)} символов\n"
    if warnings:
        response += "\n" + "\n".join(warnings) + "\n"
    response += "\nОтправь <b>токен</b> или <code>none</code> (если не нужен).\n"
    response += "🔒 Токен будет удалён из чата."

    await message.answer(response, parse_mode="HTML")
    await state.set_state(UploadStates.waiting_token)


@dp.message(UploadStates.waiting_token, F.text)
async def handle_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if token.lower() in ["none", "нет", "no", "-", "skip", "пропустить"]:
        token = ""
        token_status = "🚫 Без токена"
    elif ":" not in token or len(token) < 30:
        return await message.answer(
            "⚠️ Не похоже на токен.\n\nФормат: <code>123:ABC...</code>\n"
            "Если не нужен: <code>none</code>", parse_mode="HTML")
    else:
        token_status = "🔐 Токен принят"

    try: await message.delete()
    except: pass

    data = await state.get_data()
    bot_id = save_bot(message.from_user.id, data['filename'], token)

    bot_dir = BOTS_DIR / f"bot_{bot_id}"
    bot_dir.mkdir(exist_ok=True)
    (bot_dir / "user_bot.py").write_text(data['code'], encoding="utf-8")

    await message.answer(
        f"✅ <b>Код сохранён!</b>\n\n🆔 ID: <code>{bot_id}</code>\n"
        f"📁 {data['filename']}\n{token_status}\n\n"
        f"📦 Хост автоматически установит нужные библиотеки!\n\n"
        f"Запусти через <b>«🤖 Мои боты»</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 К моим ботам", callback_data="mybots")]]),
        parse_mode="HTML")
    await state.clear()


@dp.message(F.photo)
async def handle_random_photo(message: types.Message):
    await message.answer(
        "📸 <b>Получил фото!</b>\n\nДля загрузки бота нужен <b>.py-файл</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
            [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
        parse_mode="HTML")


# ─── Callback ─────────────────────────────────────────────

@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if is_user_banned(call.from_user.id):
        return await call.answer("🚫 Заблокированы", show_alert=True)
    try: await call.message.delete()
    except: pass
    await send_welcome(call.message)


@dp.callback_query(F.data == "buy")
async def cb_buy(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if is_user_banned(call.from_user.id):
        return await call.answer("🚫 Заблокированы", show_alert=True)

    if call.from_user.id == OWNER_ID:
        return await call.message.edit_text(
            "👑 <b>Ты — владелец!</b>\n\n<b>Безлимит</b> бесплатно.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    if is_admin(call.from_user.id):
        return await call.message.edit_text(
            "🛡 <b>Ты — админ!</b>\n\n<b>Безлимит</b> бесплатно.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить бота", callback_data="upload")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    text = ("💎 <b>Выбери тариф</b>\n\n━━━━━━━━━━━━━━━\n\n"
            "Оплата <b>подарком</b> владельцу.\n\n━━━━━━━━━━━━━━━")
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
    link = get_profile_link()
    text = (f"{plan['emoji']} <b>Тариф: {plan['name']}</b>\n\n━━━━━━━━━━━━━━━\n\n"
            f"💎 {plan['stars']}⭐\n📅 {plan['days']} дней\n\n━━━━━━━━━━━━━━━\n\n"
            f"<b>🎁 Оплата:</b>\n"
            f"1️⃣ Нажми <b>«🎁 Отправить»</b>\n"
            f"2️⃣ В профиле: ⋮ → 🎁 Подарить\n"
            f"3️⃣ Выбери подарок <b>от {plan['stars']}⭐</b>\n"
            f"4️⃣ Отправь\n"
            f"5️⃣ Нажми <b>«✅ Я отправил»</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Отправить подарок", url=link)],
        [InlineKeyboardButton(text="✅ Я отправил подарок", callback_data=f"confirm:{plan_id}")],
        [InlineKeyboardButton(text="« Тарифы", callback_data="buy")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)


@dp.callback_query(F.data.startswith("confirm:"))
async def cb_confirm_payment(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    plan_id = call.data.split(":")[1]
    plan = PLANS[plan_id]
    user_id = call.from_user.id

    await call.answer("⏳ Проверяю...")
    gift = get_pending_gift_for_plan(user_id, plan_id)

    if not gift:
        return await call.message.edit_text(
            f"❌ <b>Подарок не найден!</b>\n\nНужен подарок <b>от {plan['stars']}⭐</b>.\n"
            f"Подожди 1-2 мин и попробуй снова.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"confirm:{plan_id}")],
                [InlineKeyboardButton(text="🎁 Отправить", url=get_profile_link())],
                [InlineKeyboardButton(text="« Тарифы", callback_data="buy")]]),
            parse_mode="HTML", disable_web_page_preview=True)

    gift_id, gift_value, gift_uid = gift
    activate_gift(gift_id, plan_id)
    create_slot(user_id, plan_id, gift_uid)

    await call.message.edit_text(
        f"✅ <b>Оплата прошла!</b>\n\n🎁 {gift_value}⭐\n{plan['emoji']} {plan['name']}\n"
        f"📅 {plan['days']} дней\n\n🎉 Загружай бота!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")],
            [InlineKeyboardButton(text="📊 Мои слоты", callback_data="myslots")]]),
        parse_mode="HTML")

    try:
        await bot.send_message(OWNER_ID,
            f"💰 @{call.from_user.username or '—'} → {gift_value}⭐ → {plan['name']}",
            parse_mode="HTML")
    except: pass


@dp.callback_query(F.data == "upload")
async def cb_upload(call: types.CallbackQuery, state: FSMContext):
    if is_user_banned(call.from_user.id):
        await state.clear()
        return await call.answer("🚫 Заблокированы", show_alert=True)
    if not has_active_slot(call.from_user.id):
        await state.clear()
        return await call.answer("❌ Нет слота!", show_alert=True)

    await call.message.edit_text(
        "📤 <b>Загрузка кода</b>\n\nОтправь <b>.py-файл</b>.\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "✅ Автоустановка библиотек (aiogram, telebot, pyrogram, "
        "openai, requests, discord.py и др.)\n\n"
        "💡 Токен можно не указывать: <code>none</code>\n"
        "📏 Макс: 500 КБ",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Отмена", callback_data="back_main")]]),
        parse_mode="HTML")
    await state.set_state(UploadStates.waiting_file)


@dp.callback_query(F.data == "mybots")
async def cb_mybots(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bots = get_user_bots(call.from_user.id)
    if not bots:
        return await call.message.edit_text(
            "🤖 <b>Нет ботов</b>\n\nЗагрузи первого!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Загрузить", callback_data="upload")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    buttons = []
    for b in bots:
        status = "🟢" if b[0] in running_bots else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{status} #{b[0]} • {b[2]}", callback_data=f"bot:{b[0]}")])
    buttons.append([InlineKeyboardButton(text="« Меню", callback_data="back_main")])

    await call.message.edit_text(
        f"🤖 <b>Твои боты ({len(bots)})</b>\n\n🟢 работает • 🔴 остановлен",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@dp.callback_query(F.data.startswith("bot:"))
async def cb_bot_detail(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)

    status = "🟢 Работает" if bot_id in running_bots else "🔴 Остановлен"
    await call.message.edit_text(
        f"🤖 <b>Бот #{bot_id}</b>\n\n📁 <code>{b[2]}</code>\n📊 {status}\n📅 {b[5][:10]}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Запуск", callback_data=f"start:{bot_id}"),
             InlineKeyboardButton(text="⏹ Стоп", callback_data=f"stop:{bot_id}")],
            [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{bot_id}")],
            [InlineKeyboardButton(text="« Список", callback_data="mybots")]]),
        parse_mode="HTML")


@dp.callback_query(F.data.startswith("start:"))
async def cb_start_bot(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id:
        return await call.answer("❌ Нет доступа", show_alert=True)
    if not has_active_slot(call.from_user.id):
        return await call.answer("❌ Нет слота", show_alert=True)
    if bot_id in running_bots:
        return await call.answer("⚠️ Уже запущен", show_alert=True)

    await call.answer("⏳ Запускаю (~10 сек, устанавливаю зависимости)...")

    code_file = BOTS_DIR / f"bot_{bot_id}" / "user_bot.py"
    if not code_file.exists():
        return await call.answer("❌ Файл не найден", show_alert=True)

    code = code_file.read_text(encoding="utf-8")
    user_bot_token = b[3] or ""
    success = await start_user_bot(bot_id, code, user_bot_token)

    if success:
        await call.message.answer(f"✅ <b>Бот #{bot_id} запущен!</b>", parse_mode="HTML")
    else:
        logs = get_bot_logs(bot_id, 40)
        hint = ""
        if "Conflict" in logs or "terminated by other" in logs:
            hint = "\n\n🔴 <b>КОНФЛИКТ!</b> Токен уже используется. Получи новый у @BotFather"
        elif "Unauthorized" in logs or "401" in logs:
            hint = "\n\n🔴 <b>НЕВЕРНЫЙ ТОКЕН!</b>"
        elif "No module named" in logs:
            m = re.search(r"No module named '([^']+)'", logs)
            mod = m.group(1) if m else "?"
            hint = f"\n\n💡 Не установилось: <code>{mod}</code>"
        elif "SyntaxError" in logs:
            hint = "\n\n💡 Синтаксическая ошибка"

        logs_text = html.escape(logs[-2000:]) if logs.strip() else "📭 Пусто"
        await call.message.answer(
            f"❌ <b>Бот #{bot_id} не запустился</b>\n\n<pre>{logs_text}</pre>{hint}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Снова", callback_data=f"start:{bot_id}")],
                [InlineKeyboardButton(text="📄 Логи", callback_data=f"logs:{bot_id}")],
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{bot_id}")],
                [InlineKeyboardButton(text="« Список", callback_data="mybots")]]))


@dp.callback_query(F.data.startswith("stop:"))
async def cb_stop_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id:
        return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    await call.answer("⏹ Остановлен")


@dp.callback_query(F.data.startswith("logs:"))
async def cb_logs(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or (b[1] != call.from_user.id and not is_admin(call.from_user.id)):
        return await call.answer("❌ Нет доступа", show_alert=True)

    logs = get_bot_logs(bot_id, 50)
    logs_safe = html.escape(logs[-3000:])
    await call.message.answer(
        f"📄 <b>Логи #{bot_id}</b>\n\n<pre>{logs_safe}</pre>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton(text="« К боту", callback_data=f"bot:{bot_id}")]]),
        parse_mode="HTML")


@dp.callback_query(F.data.startswith("del:"))
async def cb_delete_bot(call: types.CallbackQuery):
    bot_id = int(call.data.split(":")[1])
    b = get_bot(bot_id)
    if not b or b[1] != call.from_user.id:
        return await call.answer("❌ Нет доступа", show_alert=True)
    await stop_user_bot(bot_id)
    delete_bot_record(bot_id)
    await call.answer("🗑 Удалён")
    await cb_mybots(call, None)


@dp.callback_query(F.data == "myslots")
async def cb_myslots(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.from_user.id == OWNER_ID:
        return await call.message.edit_text("👑 <b>Безлимит</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")
    if is_admin(call.from_user.id):
        return await call.message.edit_text("🛡 <b>Безлимит (админ)</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    slots = get_active_slots(call.from_user.id)
    if not slots:
        return await call.message.edit_text(
            "💳 <b>Нет активных слотов</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить", callback_data="buy")],
                [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
            parse_mode="HTML")

    text = f"💳 <b>Слоты ({len(slots)})</b>\n\n"
    for s in slots:
        exp = datetime.fromisoformat(s[3])
        days = (exp - datetime.now()).days
        text += f"• <b>{PLANS[s[2]]['name']}</b> — ещё {days} дн.\n"
    await call.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить ещё", callback_data="buy")],
            [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
        parse_mode="HTML")


@dp.callback_query(F.data == "help")
async def cb_help(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = ("❓ <b>Помощь</b>\n\n"
            "<b>🎁 Купить слот:</b>\n"
            "1. «💎 Купить» → выбери тариф\n"
            "2. Отправь подарок владельцу\n"
            "3. Нажми «✅ Я отправил»\n\n"
            "<b>📤 Загрузить бота:</b>\n"
            "1. «📤 Загрузить»\n"
            "2. Отправь .py-файл\n"
            "3. Отправь токен (или 'none')\n"
            "4. Запусти через «🤖 Мои боты»\n\n"
            "✅ Библиотеки ставятся автоматически")
    await call.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Владелец", url=get_profile_link())],
            [InlineKeyboardButton(text="« Меню", callback_data="back_main")]]),
        parse_mode="HTML", disable_web_page_preview=True)


# ═══════════════════════════════════════════════════════════════
# 🔐 АДМИНКА
# ═══════════════════════════════════════════════════════════════

async def show_admin_panel(message, edit=False):
    s = get_stats()
    text = (f"🔐 <b>Админ-панель</b>\n\n━━━━━━━━━━━━━━━\n\n"
            f"👥 Users: <b>{s['total_users']}</b>\n🚫 Ban: <b>{s['banned']}</b>\n"
            f"🛡 Admins: <b>{s['admins']}</b>\n💳 Slots: <b>{s['active_slots']}</b>\n"
            f"🤖 Bots: <b>{s['total_bots']}</b> (🟢 {s['running_bots']})\n"
            f"🎁 Gifts: <b>{s['total_gifts']}</b> ({s['total_stars']}⭐)")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="👥 Users", callback_data="adm:users")],
        [InlineKeyboardButton(text="🚫 Бан", callback_data="adm:ban"),
         InlineKeyboardButton(text="✅ Разбан", callback_data="adm:unban")],
        [InlineKeyboardButton(text="🛡 +Админ", callback_data="adm:addadmin"),
         InlineKeyboardButton(text="❌ -Админ", callback_data="adm:remadmin")],
        [InlineKeyboardButton(text="🖼 Приветствие", callback_data="adm:welcome")],
        [InlineKeyboardButton(text="🔄 Рестарт всех", callback_data="adm:restart")],
        [InlineKeyboardButton(text="« Меню", callback_data="back_main")]])
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(call.from_user.id):
        return await call.answer("🔐 Нет прав", show_alert=True)
    await show_admin_panel(call.message, edit=True)


@dp.callback_query(F.data == "adm:stats")
async def cb_adm_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    s = get_stats()
    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n👥 {s['total_users']}\n🚫 {s['banned']}\n"
        f"🛡 {s['admins']}\n💳 {s['active_slots']}\n"
        f"🤖 {s['total_bots']} (🟢 {s['running_bots']})\n"
        f"🎁 {s['total_gifts']} ({s['total_stars']}⭐)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")


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
    for u in users:
        ban = "🚫" if u[4] else "✓"
        adm = "🛡" if u[3] else ""
        uname = f"@{u[1]}" if u[1] else "—"
        text += f"{ban}{adm} <code>{u[0]}</code> {uname}\n"
    await call.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")


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
    if call.from_user.id != OWNER_ID:
        return await call.answer("⚠️ Только владелец", show_alert=True)
    await call.message.edit_text("🛡 <b>Добавить админа</b>\n\nID или @username\nОтмена: /cancel", parse_mode="HTML")
    await state.set_state(AdminStates.addadmin)


@dp.callback_query(F.data == "adm:remadmin")
async def cb_remadmin(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return await call.answer("⚠️ Только владелец", show_alert=True)
    admins = get_all_admins()
    if not admins: return await call.answer("📭 Нет", show_alert=True)
    buttons = [[InlineKeyboardButton(text=f"❌ {a[1] or a[2] or a[0]}",
                callback_data=f"remadm:{a[0]}")] for a in admins]
    buttons.append([InlineKeyboardButton(text="« Отмена", callback_data="admin")])
    await call.message.edit_text("❌ <b>Удалить админа:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@dp.callback_query(F.data.startswith("remadm:"))
async def cb_remadm_confirm(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID: return
    uid = int(call.data.split(":")[1])
    remove_admin(uid)
    await call.answer("✅ Удалён")
    await show_admin_panel(call.message, edit=True)


@dp.callback_query(F.data == "adm:welcome")
async def cb_welcome(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        return await call.answer("⚠️ Только владелец", show_alert=True)
    status = "✅" if WELCOME_IMAGE.exists() else "📭"
    await call.message.edit_text(
        f"🖼 <b>Приветствие</b>\n\n{status}\n\nОтправь фото или <code>delete</code>\nОтмена: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]),
        parse_mode="HTML")
    await state.set_state(AdminStates.welcome_photo)


@dp.callback_query(F.data == "adm:restart")
async def cb_restart_all(call: types.CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer("⏳ Перезапуск...")
    for bid in list(running_bots.keys()):
        await stop_user_bot(bid)

    restarted = 0
    for b in get_all_bots():
        bid, uid, _, tok, status, _ = b
        if is_user_banned(uid): continue
        if uid != OWNER_ID and not is_admin(uid) and not has_active_slot(uid): continue
        code_file = BOTS_DIR / f"bot_{bid}" / "user_bot.py"
        if code_file.exists():
            code = code_file.read_text(encoding="utf-8")
            if await start_user_bot(bid, code, tok or ""):
                restarted += 1

    await call.message.answer(f"🔄 Перезапущено: {restarted}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Админка", callback_data="admin")]]))


# ═══════════════════════════════════════════════════════════════
# 🎯 MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("=" * 50)
    logger.info("🤖 BotHost v2.0 запущен")
    logger.info(f"👤 Владелец: {OWNER_ID}")
    logger.info(f"📁 Data: {DATA_DIR}")
    logger.info("=" * 50)

    await restore_running_bots()
    asyncio.create_task(check_gifts())
    asyncio.create_task(monitor_bots())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Выход")
