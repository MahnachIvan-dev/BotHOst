# 🤖 BotHost — Хостинг Telegram-ботов

Полноценная платформа для хостинга Telegram-ботов с оплатой через **Telegram Gifts** (подарки).

---

## ⚡ БЫСТРАЯ УСТАНОВКА

**4 сервиса: GitHub + Vercel + Supabase (БД) + Railway (runner)**  
**Стоимость:** $5/месяц (только runner, всё остальное бесплатно!)  
**Время:** ~30 минут

### 📚 Документация:

| Файл | Описание |
|------|----------|
| **[DEPLOYMENT.md](./DEPLOYMENT.md)** | 🎯 **ГЛАВНАЯ ИНСТРУКЦИЯ** — полный гайд по деплою и подключению |
| [QUICKSTART.md](./QUICKSTART.md) | Быстрый старт (16 шагов) |
| На сайте: [/quickstart](https://your-app.vercel.app/quickstart) | Визуальная инструкция |

### 🤖 Архитектура:

```
GitHub ($0) + Vercel ($0, сайт) + Supabase ($0, БД) + Railway ($5, runner)
```

- **Telegram-бот** — интерфейс пользователя (оплата Stars, загрузка, управление)
- **Сайт (Vercel)** — сервер (API, админка, фронтенд)
- **БД (Supabase)** — бесплатная PostgreSQL 500 MB
- **Runner (Railway)** — запуск Python-ботов в Docker
- **Оплата** — только через **Telegram Stars** (звёзды идут владельцу)

---

## ✨ Возможности

- 🚀 **Загрузка Python-ботов** через сайт или Telegram
- 🎁 **Оплата через Telegram Gifts** — дарите подарки владельцу, слоты активируются автоматически
- 🎟️ **Промокоды** на бесплатные слоты
- 🔒 **Безопасность** — токены не указываются в коде
- 🛡️ **Валидация кода** — проверка, что это именно Telegram-бот
- 🐳 **Изоляция** — каждый бот в Docker-контейнере
- 📊 **Админ-панель** на сайте и в Telegram
- 💳 **Тарифы**: неделя (15⭐), 2 недели (25⭐), месяц (50⭐)

## 🏗️ Архитектура

### Сайт (этот репозиторий)
- **Next.js 16** с App Router
- **PostgreSQL** через Drizzle ORM
- **Tailwind CSS** для стилей
- Деплой на **Vercel**

### Telegram-бот (отдельный runner-сервер)
- **Python** с библиотекой **aiogram 3.x**
- Запускается на **Railway / Render / VPS**
- Код бота доступен на странице `/bot-setup`

## 📋 Тарифы

| План | Длительность | Цена | Слотов |
|------|--------------|------|--------|
| Неделя | 7 дней | 15 ⭐ | 1 |
| 2 недели | 14 дней | 25 ⭐ | 1 |
| Месяц | 30 дней | 50 ⭐ | 1 |

## 🚀 Быстрый старт

### 📚 ПОЛНАЯ ИНСТРУКЦИЯ ДЛЯ НОВИЧКОВ

Если вы впервые деплоите проект — откройте **[INSTALL.md](./INSTALL.md)**

Там пошагово расписано:
- Где регистрироваться
- Что скачивать
- Куда что вставлять
- Как проверить что всё работает

**Время:** ~2 часа  
**Стоимость:** ~$5/месяц

---

### ⚡ Быстрая установка (для опытных)

```bash
git clone https://github.com/your-username/bothost.git
cd bothost
npm install

# Создайте .env
DATABASE_URL=postgresql://user:password@localhost:5432/bothost

# Примените схему
npx drizzle-kit push

# Запустите
npm run dev
```

Откройте http://localhost:3000

## 🌐 Деплой на Vercel

Подробная инструкция на странице `/vercel-deploy` или в [документации](./DEPLOY.md).

### Кратко:

1. Создайте проект на Vercel
2. Подключите GitHub репозиторий
3. Добавьте PostgreSQL (Vercel Postgres / Neon / Supabase)
4. Настройте переменные окружения:
   ```
   DATABASE_URL=postgresql://...
   TELEGRAM_BOT_TOKEN=...
   ADMIN_TELEGRAM_ID=...
   ```
5. Примените схему: `npx drizzle-kit push`
6. Готово!

## 🤖 Настройка Telegram-бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен
3. Скопируйте код бота со страницы `/bot-setup`
4. Запустите на runner-сервере (Railway / Render / VPS)
5. Настройте webhook или polling

### Переменные окружения для бота:

```env
BOT_TOKEN=1234567890:ABCdefGhI...
WEBSITE_URL=https://bothost.vercel.app
OWNER_TELEGRAM_ID=123456789
```

## 📁 Структура проекта

```
src/
├── app/
│   ├── page.tsx              # Главная страница
│   ├── upload/page.tsx       # Загрузка бота
│   ├── dashboard/page.tsx    # Личный кабинет
│   ├── admin/page.tsx        # Админ-панель
│   ├── bot-setup/page.tsx    # Код Telegram-бота
│   ├── vercel-deploy/page.tsx # Инструкция по деплою
│   ├── buy/[planId]/page.tsx # Страница оплаты
│   └── api/
│       ├── bots/             # API для ботов
│       ├── subscriptions/    # API для подписок
│       ├── promo/            # API для промокодов
│       ├── admin/            # API админки
│       └── health/           # Healthcheck
├── db/
│   ├── schema.ts             # Схема БД
│   └── index.ts              # Подключение к БД
└── lib/
    ├── constants.ts          # Константы и тарифы
    ├── db-operations.ts      # Операции с БД
    └── validate-bot.ts       # Валидация Python-кода
```

## 🔐 Безопасность

### Валидация кода ботов

Система проверяет загруженный Python-код:

1. **Наличие Telegram-библиотек** (aiogram, telebot, pyrogram и др.)
2. **Отсутствие хардкоднутых токенов** (regex-проверка)
3. **Использование переменных окружения** для токенов
4. **Отсутствие опасных операций** (rm, subprocess и т.д.)
5. **Базовая проверка синтаксиса**

### Пример правильного кода:

```python
import os
from aiogram import Bot, Dispatcher

# ✅ ПРАВИЛЬНО — токен из окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
```

### Пример неправильного кода:

```python
# ❌ НЕПРАВИЛЬНО — хардкоднутый токен
BOT_TOKEN = "1234567890:ABCdefGhI..."
bot = Bot(token=BOT_TOKEN)
```

## 💳 Telegram Stars

Оплата проходит через **Telegram Stars** (валюта XTR):

- Звёзды поступают **напрямую владельцу бота**
- Комиссия Telegram: 0% (на момент 2026)
- Вывод через BotFather → Bot Settings → Payments → Telegram Stars Balance

## 🎁 Промокоды

Администраторы могут создавать промокоды через:

- Веб-админку: `/admin`
- Telegram-бота: команда `/admin`

Промокоды дают **бесплатный слот** на выбранный период.

## 🛠️ Технологии

- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **Backend**: Next.js API Routes, Drizzle ORM
- **Database**: PostgreSQL
- **Telegram**: aiogram 3.x (Python)
- **Deploy**: Vercel (сайт), Railway/Render (бот)

## 📝 Лицензия

MIT

## 🤝 Поддержка

По всем вопросам обращайтесь к администратору или создайте Issue в репозитории.

---

**BotHost** — хостинг Telegram-ботов нового поколения ⭐
