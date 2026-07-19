# 🚀 BotHost Runner

Runner-сервер для BotHost — реально запускает Python-ботов пользователей в изолированных Docker-контейнерах + Telegram-бот для управления и отслеживания подарков.

## 📦 Что внутри

- **`runner.py`** — FastAPI-сервер, принимает команды от сайта, запускает ботов в Docker
- **`bot.py`** — Telegram-бот: интерфейс пользователя + отслеживание подарков владельцу

## 🏗️ Архитектура

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Vercel        │ ────> │   Runner        │ ────> │ Docker          │
│   (Сайт + API)  │       │ (FastAPI + TBot)│       │ (Боты user'ов)  │
└─────────────────┘       └─────────────────┘       └─────────────────┘
         │                         │
         │                         └───> Telegram (отслеживает подарки)
         └───> PostgreSQL (БД)
```

## 💰 Оплата через подарки

Пользователь дарит подарок **владельцу** через Telegram → владелец получает подарок → runner-сервер это видит через Userbot API → активирует слот.

### Стоимость подарка → План:
- 🎁 **15+ ⭐** → слот на **1 неделю**
- 🎁 **25+ ⭐** → слот на **2 недели**
- 🎁 **50+ ⭐** → слот на **1 месяц**

## 🚀 Деплой на Railway (рекомендуется)

### Шаг 1: Подготовка

1. Форкните репозиторий BotHost
2. Зарегистрируйтесь на [railway.app](https://railway.app)
3. Установите Railway CLI: `npm i -g @railway/cli`

### Шаг 2: Деплой сайта на Vercel

```bash
cd bothost
vercel --prod
```

Добавьте переменные:
```
DATABASE_URL=postgresql://...
RUNNER_URL=https://your-runner.railway.app
RUNNER_SECRET=your_secret_here
ADMIN_TELEGRAM_ID=123456789
```

### Шаг 3: Деплой Runner на Railway

```bash
cd runner
railway init
railway up
```

Добавьте переменные в Railway:
```
BOT_TOKEN=1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
OWNER_TELEGRAM_ID=123456789
OWNER_PHONE=+79991234567
OWNER_API_ID=12345678
OWNER_API_HASH=abcdef1234567890abcdef1234567890
WEBSITE_URL=https://bothost.vercel.app
RUNNER_SECRET=your_secret_here
PORT=8000
```

### Шаг 4: Получение Telegram API credentials

Для Userbot (отслеживание подарков):

1. Зайдите на https://my.telegram.org
2. Войдите с номером владельца
3. **API development tools** → Create application
4. Скопируйте `api_id` и `api_hash`
5. Добавьте в переменные:
   - `OWNER_API_ID`
   - `OWNER_API_HASH`
   - `OWNER_PHONE`

### Шаг 5: Настройка Docker

На Railway Docker уже доступен. Для VPS:

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Запуск runner с docker.sock
docker build -t bothost-runner .
docker run -d \
  --name runner \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8000:8000 \
  --env-file .env \
  bothost-runner
```

## 🖥️ Деплой на VPS (Hetzner/DigitalOcean)

### Шаг 1: Аренда VPS

Рекомендую:
- **Hetzner** CX22: €4.35/мес (2 vCPU, 4 GB RAM)
- **DigitalOcean** Basic: $6/мес (1 vCPU, 1 GB RAM)
- **Contabo** Cloud VPS S: €4.99/мес (4 vCPU, 8 GB RAM)

### Шаг 2: Настройка сервера

```bash
# SSH подключение
ssh root@your-server-ip

# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sh

# Установка Python 3.11
apt install -y python3.11 python3.11-venv python3-pip git

# Клонирование проекта
git clone https://github.com/your-username/bothost.git
cd bothost/runner

# Создание venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Шаг 3: Конфигурация

```bash
nano .env
```

Вставьте:
```env
BOT_TOKEN=1234567890:ABCdef...
OWNER_TELEGRAM_ID=123456789
OWNER_PHONE=+79991234567
OWNER_API_ID=12345678
OWNER_API_HASH=abcdef1234567890...
WEBSITE_URL=https://bothost.vercel.app
RUNNER_SECRET=very_secret_string
PORT=8000
BOTS_DIR=/opt/bothost/bots
```

### Шаг 4: Запуск через systemd

Создайте `/etc/systemd/system/bothost-runner.service`:

```ini
[Unit]
Description=BotHost Runner
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bothost/runner
Environment="PATH=/opt/bothost/runner/venv/bin"
ExecStart=/opt/bothost/runner/venv/bin/python runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Создайте `/etc/systemd/system/bothost-bot.service`:

```ini
[Unit]
Description=BotHost Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bothost/runner
Environment="PATH=/opt/bothost/runner/venv/bin"
ExecStart=/opt/bothost/runner/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите:
```bash
systemctl daemon-reload
systemctl enable bothost-runner bothost-bot
systemctl start bothost-runner bothost-bot
```

### Шаг 5: Nginx + SSL

```bash
apt install -y nginx certbot python3-certbot-nginx
```

Создайте `/etc/nginx/sites-available/runner`:

```nginx
server {
    server_name runner.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/runner /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
certbot --nginx -d runner.yourdomain.com
```

## 🔒 Безопасность

### Изоляция ботов

Каждый бот пользователя запускается в отдельном Docker-контейнере с ограничениями:

- **RAM**: 256 MB (настраивается через `MAX_MEMORY_MB`)
- **CPU**: 0.5 cores (настраивается через `MAX_CPU`)
- **Network**: bridge (можно отключить)
- **Restart**: on-failure:3

### Секреты

- `RUNNER_SECRET` — для аутентификации запросов от сайта
- Токены ботов пользователей передаются только через env-переменные контейнера
- Токены НЕ сохраняются в БД сайта (только в runner)

### Файрвол

На VPS настройте UFW:
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow from YOUR_VERCEL_IP to any port 8000
ufw enable
```

## 📊 Мониторинг

### Логи

```bash
# Runner
journalctl -u bothost-runner -f

# Telegram Bot
journalctl -u bothost-bot -f

# Контейнеры пользователей
docker logs bothost_bot_123
```

### Метрики

Используйте `docker stats` для мониторинга:
```bash
docker stats --no-stream
```

### Алерты

Добавьте в `bot.py` уведомления владельцу:
```python
if container.status == "error":
    await bot.send_message(OWNER_TELEGRAM_ID, f"⚠️ Бот {bot_id} упал!")
```

## 🔄 Обновления

```bash
cd /opt/bothost/runner
git pull
systemctl restart bothost-runner bothost-bot
```

## 💾 Бэкапы

### Бэкап PostgreSQL (сайт)

```bash
# На Vercel/Neon: автоматические бэкапы
# Локально:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Бэкап кода ботов

```bash
tar -czf bots_backup_$(date +%Y%m%d).tar.gz /opt/bothost/bots
# Загрузить в S3/R2:
aws s3 cp bots_backup_*.tar.gz s3://your-bucket/
```

## 🆘 Troubleshooting

### Docker permission denied

```bash
usermod -aG docker $USER
newgrp docker
```

### Порт 8000 занят

```bash
lsof -i :8000
kill -9 <PID>
```

### Контейнер не запускается

```bash
docker logs bothost_bot_123
docker inspect bothost_bot_123
```

### Подарки не отслеживаются

- Проверьте `OWNER_API_ID`, `OWNER_API_HASH`, `OWNER_PHONE`
- Убедитесь, что номер владельца совпадает
- Проверьте, что 2FA отключена (или передайте пароль)

## 📈 Масштабирование

### Вертикальное

Увеличьте CPU/RAM на VPS:
- Hetzner: CX32 (4 vCPU, 8 GB) за €8.35/мес
- DigitalOcean: s-4vcpu-8gb за $48/мес

### Горизонтальное

Запустите несколько runner'ов, сайт будет балансировать:
```
runner-1.example.com
runner-2.example.com
runner-3.example.com
```

Добавьте в сайт логику выбора runner'а по `bot_id % runners_count`.

## 🎯 Итоговая стоимость

| Компонент | План | Цена/мес |
|-----------|------|----------|
| Vercel (сайт) | Hobby | $0 |
| Neon (БД) | Free | $0 |
| Railway (runner) | Starter | $5 |
| **Итого** | | **$5** |

Или на VPS:
| Компонент | План | Цена/мес |
|-----------|------|----------|
| Vercel (сайт) | Hobby | $0 |
| Neon (БД) | Free | $0 |
| Hetzner VPS | CX22 | €4.35 |
| **Итого** | | **~$5** |

---

**Готово!** Ваш BotHost работает и принимает подарки 🎁
