"""
Runner — менеджер для запуска Python-ботов пользователей в изолированных контейнерах
Запускается как FastAPI-сервер, принимает команды от сайта
"""
import os
import asyncio
import subprocess
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === КОНФИГУРАЦИЯ ===
RUNNER_SECRET = os.environ.get("RUNNER_SECRET", "secret123")
BOTS_DIR = Path(os.environ.get("BOTS_DIR", "/tmp/bothost_bots"))
BOTS_DIR.mkdir(parents=True, exist_ok=True)

# Лимиты для каждого бота
MAX_MEMORY_MB = int(os.environ.get("MAX_MEMORY_MB", "256"))
MAX_CPU = float(os.environ.get("MAX_CPU", "0.5"))
MAX_RUNTIME_HOURS = int(os.environ.get("MAX_RUNTIME_HOURS", "720"))  # 30 дней


@dataclass
class BotContainer:
    bot_id: int
    container_id: str
    user_id: int
    started_at: datetime
    status: str  # running, stopped, error


# Реестр контейнеров
containers: Dict[int, BotContainer] = {}


# === MODELS ===

class RunBotRequest(BaseModel):
    bot_id: int
    user_id: int
    filename: str
    code: str
    bot_token: str
    secret: str


class StopBotRequest(BaseModel):
    bot_id: int
    secret: str


class ActionRequest(BaseModel):
    bot_id: int
    secret: str


# === HELPERS ===

def verify_secret(secret: str):
    if secret != RUNNER_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")


def is_docker_available() -> bool:
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


# === RUN BOT ===

def run_bot_in_docker(req: RunBotRequest) -> BotContainer:
    """Запускает бота пользователя в Docker-контейнере"""
    bot_dir = BOTS_DIR / f"bot_{req.bot_id}"
    bot_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем код
    bot_file = bot_dir / req.filename
    bot_file.write_text(req.code, encoding="utf-8")
    
    # Создаём requirements.txt
    req_file = bot_dir / "requirements.txt"
    req_file.write_text("aiogram\npython-telegram-bot\npyTelegramBotAPI\npyrogram\ntelethon\n", encoding="utf-8")
    
    # Создаём Dockerfile
    dockerfile = bot_dir / "Dockerfile"
    dockerfile.write_text(f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY {req.filename} bot.py
CMD ["python", "bot.py"]
""", encoding="utf-8")
    
    container_name = f"bothost_bot_{req.bot_id}"
    
    try:
        # Удаляем старый контейнер, если был
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True
        )
        
        # Строим образ
        logger.info(f"Строю образ для бота {req.bot_id}...")
        build_result = subprocess.run(
            ["docker", "build", "-t", f"bothost:{req.bot_id}", "."],
            cwd=bot_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if build_result.returncode != 0:
            raise RuntimeError(f"Docker build failed: {build_result.stderr}")
        
        # Запускаем контейнер с ограничениями
        logger.info(f"Запускаю контейнер для бота {req.bot_id}...")
        run_result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "--memory", f"{MAX_MEMORY_MB}m",
                "--cpus", str(MAX_CPU),
                "--network", "bridge",
                "--restart", "on-failure:3",
                "-e", f"BOT_TOKEN={req.bot_token}",
                f"bothost:{req.bot_id}"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if run_result.returncode != 0:
            raise RuntimeError(f"Docker run failed: {run_result.stderr}")
        
        container_id = run_result.stdout.strip()[:12]
        
        container = BotContainer(
            bot_id=req.bot_id,
            container_id=container_id,
            user_id=req.user_id,
            started_at=datetime.now(),
            status="running"
        )
        
        containers[req.bot_id] = container
        logger.info(f"Бот {req.bot_id} запущен в контейнере {container_id}")
        
        return container
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота {req.bot_id}: {e}")
        raise


def run_bot_direct(req: RunBotRequest) -> BotContainer:
    """Fallback: запуск без Docker (для локальной разработки)"""
    bot_dir = BOTS_DIR / f"bot_{req.bot_id}"
    bot_dir.mkdir(parents=True, exist_ok=True)
    
    bot_file = bot_dir / req.filename
    bot_file.write_text(req.code, encoding="utf-8")
    
    log_file = bot_dir / "bot.log"
    
    env = os.environ.copy()
    env["BOT_TOKEN"] = req.bot_token
    
    process = subprocess.Popen(
        ["python", req.filename],
        cwd=bot_dir,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True
    )
    
    container = BotContainer(
        bot_id=req.bot_id,
        container_id=f"proc_{process.pid}",
        user_id=req.user_id,
        started_at=datetime.now(),
        status="running"
    )
    
    containers[req.bot_id] = container
    return container


# === FASTAPI APP ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Runner запущен")
    logger.info(f"Docker доступен: {is_docker_available()}")
    yield
    # Cleanup: останавливаем все контейнеры
    for bot_id in list(containers.keys()):
        try:
            stop_container(bot_id)
        except Exception:
            pass
    logger.info("Runner остановлен")


app = FastAPI(title="BotHost Runner", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "docker_available": is_docker_available(),
        "running_bots": len(containers)
    }


@app.post("/run-bot")
async def api_run_bot(req: RunBotRequest):
    verify_secret(req.secret)
    
    if req.bot_id in containers:
        raise HTTPException(400, "Bot already running")
    
    try:
        if is_docker_available():
            container = run_bot_in_docker(req)
        else:
            logger.warning("Docker недоступен, использую direct-запуск")
            container = run_bot_direct(req)
        
        return {
            "status": "running",
            "container_id": container.container_id,
            "started_at": container.started_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/stop-bot")
async def api_stop_bot(req: StopBotRequest):
    verify_secret(req.secret)
    
    if req.bot_id not in containers:
        raise HTTPException(404, "Bot not running")
    
    try:
        stop_container(req.bot_id)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/bot-status/{bot_id}")
async def api_bot_status(bot_id: int, secret: str):
    verify_secret(secret)
    
    if bot_id not in containers:
        return {"status": "not_running"}
    
    container = containers[bot_id]
    
    # Проверяем, жив ли контейнер
    if is_docker_available():
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container.container_id],
            capture_output=True,
            text=True
        )
        status = result.stdout.strip() if result.returncode == 0 else "unknown"
    else:
        status = container.status
    
    # Читаем логи
    logs = ""
    try:
        if is_docker_available():
            result = subprocess.run(
                ["docker", "logs", "--tail", "100", container.container_id],
                capture_output=True,
                text=True,
                timeout=5
            )
            logs = result.stdout + result.stderr
        else:
            log_file = BOTS_DIR / f"bot_{bot_id}" / "bot.log"
            if log_file.exists():
                logs = log_file.read_text(encoding="utf-8", errors="ignore")[-5000:]
    except Exception:
        pass
    
    return {
        "status": status,
        "container_id": container.container_id,
        "started_at": container.started_at.isoformat(),
        "uptime_seconds": (datetime.now() - container.started_at).total_seconds(),
        "logs": logs
    }


@app.get("/all-bots")
async def api_all_bots(secret: str):
    verify_secret(secret)
    return {
        "bots": [asdict(c) for c in containers.values()]
    }


def stop_container(bot_id: int):
    container = containers.get(bot_id)
    if not container:
        return
    
    if is_docker_available() and not container.container_id.startswith("proc_"):
        subprocess.run(
            ["docker", "rm", "-f", container.container_id],
            capture_output=True
        )
    else:
        # Direct process
        try:
            pid = int(container.container_id.replace("proc_", ""))
            os.kill(pid, 15)  # SIGTERM
        except Exception:
            pass
    
    del containers[bot_id]
    logger.info(f"Бот {bot_id} остановлен")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
