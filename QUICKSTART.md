# 🚀 УПРОЩЁННАЯ ИНСТРУКЦИЯ ПО УСТАНОВКЕ

**4 сервиса: GitHub + Vercel + Supabase (БД) + Railway (runner)**

Время: ~1 час  
Стоимость: **$5/месяц** (только за runner, всё остальное бесплатно!)  
Сложность: для новичков

---

## 📋 Что нужно

### Аккаунты (регистрация):
1. **GitHub** — https://github.com (бесплатно)
2. **Vercel** — https://vercel.com (бесплатно, через GitHub)
3. **Supabase** — https://supabase.com (бесплатно, БД)
4. **Railway** — https://railway.app ($5 trial, runner)

### Программы (установить на компьютер):
1. **Git** — https://git-scm.com
2. **Node.js** — https://nodejs.org (LTS версия)
3. **VSCode** — https://code.visualstudio.com (опционально)

---

## 🎯 Пошаговая инструкция

### Шаг 1: Регистрация на GitHub

1. Откройте https://github.com/signup
2. Введите email, придумайте пароль и username
3. Подтвердите email
4. **Готово!**

---

### Шаг 2: Загрузка проекта на GitHub

1. Откройте https://github.com/new
2. Repository name: `bothost`
3. Public или Private (на ваш выбор)
4. **НЕ ставьте** галочки "Add README", "Add .gitignore"
5. Нажмите **"Create repository"**

**На вашем компьютере:**
```bash
# Откройте терминал (PowerShell на Windows, Terminal на Mac)
cd ~/Desktop  # или куда хотите скачать

# Скачайте проект (замените на свой username)
git clone https://github.com/ВАШ_USERNAME/bothost.git
cd bothost

# Если проекта ещё нет на GitHub — загрузите:
git add .
git commit -m "Initial commit"
git push -u origin main
```

---

### Шаг 3: Регистрация на Vercel

1. Откройте https://vercel.com/signup
2. Нажмите **"Continue with GitHub"**
3. Разрешите доступ
4. **Готово!**

---

### Шаг 4: Регистрация на Railway

1. Откройте https://railway.app
2. Нажмите **"Start a New Project"**
3. Выберите **"Login with GitHub"**
4. Разрешите доступ
5. **Готово!**

**Railway даёт $5 бесплатно** на первые проекты (хватит на месяц тестирования).

---

### Шаг 5: Создание PostgreSQL базы на Supabase (БЕСПЛАТНО)

1. Откройте https://supabase.com/dashboard
2. Нажмите **"New Project"**
3. Заполните:
   - **Name:** `bothost`
   - **Database Password:** придумайте надёжный пароль (сохраните!)
   - **Region:** ближайший к вам (например, Frankfurt)
   - **Pricing Plan:** Free
4. Нажмите **"Create new project"**, подождите 2-3 минуты
5. В левом меню: **Settings** (⚙️) → **Database**
6. Найдите раздел **"Connection string"**
7. Выберите **"Transaction"** pooler
8. Скопируйте строку:

```
postgresql://postgres.abcdefgh:your_password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**⚠️ Сохраните эту строку как `DATABASE_URL`**

**Преимущества Supabase:**
- ✅ Бесплатно 500 MB
- ✅ Удобный SQL Editor в браузере
- ✅ Table Editor для просмотра данных
- ✅ Автоматические бэкапы

---

### Шаг 6: Создание Telegram-бота

1. Откройте Telegram
2. Найдите **@BotFather** (с синей галочкой ✓)
3. Отправьте `/newbot`
4. Придумайте имя: `Мой Бот Хост`
5. Придумайте username: `MyBotHost_bot` (должен заканчиваться на `bot`)
6. BotFather пришлёт токен:
```
7123456789:AAHq1234567890abcdefghijklmnopqrstuv
```

**Сохраните этот токен как `BOT_TOKEN`**

---

### Шаг 7: Получение Telegram ID

1. В Telegram найдите **@userinfobot**
2. Нажмите **Start**
3. Получите свой ID:
```
Id: 5291847362
```

**Сохраните как `OWNER_TELEGRAM_ID` и `ADMIN_TELEGRAM_ID`**

---

### Шаг 8: Получение API credentials (для подарков)

**Это нужно чтобы бот видел подарки владельцу.**

1. Откройте https://my.telegram.org
2. Войдите с **номером телефона владельца**
3. Получите код в Telegram, введите его
4. Нажмите **"API development tools"**
5. Если впервые — заполните:
   - App title: `BotHost`
   - Short name: `bothost`
   - Platform: `Desktop`
6. Нажмите **"Create application"**
7. Сохраните:
   - `App api_id`: `2937156`
   - `App api_hash`: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

**Сохраните как `OWNER_API_ID` и `OWNER_API_HASH`**

---

### Шаг 9: Деплой сайта на Vercel

1. Откройте https://vercel.com/new
2. Найдите репозиторий `bothost`
3. Нажмите **"Import"**

**Добавьте переменные окружения** (Environment Variables):

| Key | Value | Где взять |
|-----|-------|-----------|
| `DATABASE_URL` | `postgresql://postgres:xxx@monorail.proxy.rlwy.net:12345/railway` | Railway → PostgreSQL → Connect → Public Network |
| `ADMIN_TELEGRAM_ID` | `5291847362` | @userinfobot |
| `RUNNER_SECRET` | `mysupersecret123` | Придумайте сами (20+ символов) |
| `BOT_USERNAME` | `MyBotHost_bot` | Username вашего бота БЕЗ @ |
| `RUNNER_URL` | `https://runner-production.up.railway.app` | Пока оставьте так, обновим позже |

4. Нажмите **"Deploy"**
5. Подождите 2-3 минуты
6. **Сохраните URL сайта:** `https://bothost-xxxx.vercel.app`

---

### Шаг 10: Применение схемы базы данных

**На вашем компьютере:**

```bash
cd bothost

# Создайте файл .env с одной строкой:
echo "DATABASE_URL=postgresql://postgres.abcdefgh:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres" > .env

# Установите зависимости
npm install

# Примените схему (создаст таблицы в БД)
npx drizzle-kit push
```

**Проверка в Supabase:**
1. Откройте https://supabase.com/dashboard
2. Выберите ваш проект
3. В левом меню: **Table Editor**
4. Должны появиться таблицы: `users`, `bots`, `subscriptions`, `promo_codes`, `promo_uses`, `payments`

---

### Шаг 11: Деплой Runner на Railway

**В том же проекте Railway** (где уже есть PostgreSQL):

1. Нажмите **"+ New"**
2. Выберите **"GitHub Repo"**
3. Найдите `bothost`
4. **ВАЖНО:** После импорта откройте **Settings**
5. Найдите **"Root Directory"**
6. Впишите: `runner`
7. Нажмите **Save**

**Добавьте переменные** (Variables):

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | `7123456789:AAHq...` (из BotFather) |
| `OWNER_TELEGRAM_ID` | `5291847362` (ваш ID) |
| `OWNER_PHONE` | `+79991234567` (номер владельца) |
| `OWNER_API_ID` | `2937156` (из my.telegram.org) |
| `OWNER_API_HASH` | `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6` |
| `WEBSITE_URL` | `https://bothost-xxxx.vercel.app` (URL сайта из шага 9) |
| `RUNNER_SECRET` | `mysupersecret123` (**ТОТ ЖЕ** что на Vercel!) |
| `PORT` | `8000` |

**ВАЖНО:** Runner **НЕ использует** базу данных напрямую (он только запускает ботов в Docker). Поэтому `DATABASE_URL` в Railway добавлять НЕ нужно.

---

### Шаг 12: Получение публичного URL runner'а

1. В Railway → ваш runner-сервис
2. Перейдите в **Settings** → **Networking**
3. Нажмите **"Generate Domain"**
4. Получите: `https://bothost-runner-xxxx.up.railway.app`

**Сохраните этот URL!**

---

### Шаг 13: Обновление RUNNER_URL на Vercel

1. Откройте https://vercel.com → ваш проект
2. **Settings** → **Environment Variables**
3. Найдите `RUNNER_URL`
4. Измените на: `https://bothost-runner-xxxx.up.railway.app`
5. Нажмите **Save**
6. Перейдите в **Deployments**
7. Нажмите три точки у последнего деплоя → **"Redeploy"**
8. Подождите 2-3 минуты

---

### Шаг 14: Проверка работы

**1. Сайт:**
```
https://bothost-xxxx.vercel.app
```
Должна открыться главная страница.

**2. Healthcheck:**
```
https://bothost-xxxx.vercel.app/api/health
```
Должно показать: `{"ok":true}`

**3. Runner:**
```
https://bothost-runner-xxxx.up.railway.app/health
```
Должно показать:
```json
{
  "status": "ok",
  "docker_available": true,
  "running_bots": 0
}
```

**4. Telegram-бот:**
- Откройте `@MyBotHost_bot` в Telegram
- Нажмите Start
- Должно появиться приветствие

---

### Шаг 15: Настройка админки

1. Откройте `https://bothost-xxxx.vercel.app/admin`
2. Введите свой Telegram ID
3. Увидите: "Недостаточно прав"

**Чтобы стать админом через Supabase:**

1. Откройте https://supabase.com/dashboard
2. Выберите ваш проект
3. В левом меню: **SQL Editor**
4. Нажмите **"New query"**
5. Вставьте:
```sql
UPDATE users SET is_admin = true WHERE telegram_id = '5291847362';
```
(замените на свой ID)
6. Нажмите **"Run"**
7. Перезайдите в админку — теперь работает!

---

### Шаг 16: Тест оплаты подарком

1. Откройте профиль **владельца** в Telegram (свой собственный)
2. Нажмите **"🎁 Подарить"**
3. Выберите подарок стоимостью **от 15 звёзд**
4. Отправьте подарок себе
5. В течение минуты runner увидит подарок
6. Бот пришлёт: "✅ Слот активирован!"

---

## 🎉 ГОТОВО!

Ваш BotHost полностью работает!

**Что у вас есть:**
- ✅ Сайт на Vercel
- ✅ База данных на Railway
- ✅ Runner-сервер на Railway
- ✅ Telegram-бот с оплатой через подарки

**Стоимость:** ~$5/месяц (Railway)

---

## 📊 Итоговая архитектура

```
┌─────────────────┐
│   GitHub        │ ← Код (бесплатно)
└─────────────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   Vercel        │  │   Railway       │
│   (сайт)        │  │   (runner)      │
│   бесплатно     │  │   $5/мес        │
└─────────────────┘  └─────────────────┘
         │                  │
         ▼                  ├─ FastAPI
┌─────────────────┐         └─ Telegram Bot
│   Supabase      │
│   (БД)          │
│   бесплатно     │
└─────────────────┘
```

**4 сервиса, из них 3 бесплатных!** 🎯
- GitHub: $0
- Vercel: $0
- Supabase: $0
- Railway: $5/мес

**Итого: $5/месяц**

---

## 🆘 Частые проблемы

### ❌ "DATABASE_URL is required"

**Решение:**
- Проверьте что `DATABASE_URL` добавлен в Vercel
- Используйте **публичный** URL из Railway (monorail.proxy.rlwy.net)

---

### ❌ Бот не отвечает

**Решение:**
- Проверьте логи Railway: ваш сервис → Deployments → последний → View Logs
- Убедитесь что `BOT_TOKEN` правильный
- Проверьте что Root Directory = `runner`

---

### ❌ Подарки не отслеживаются

**Решение:**
- Проверьте что добавлены все переменные:
  - `OWNER_PHONE` (с +7)
  - `OWNER_API_ID`
  - `OWNER_API_HASH`
- Номер должен совпадать с my.telegram.org
- При первом запуске Telethon может попросить код — смотрите логи Railway

---

### ❌ "403 Invalid secret"

**Решение:**
- Убедитесь что `RUNNER_SECRET` **одинаковый** на Vercel и Railway

---

### ❌ Runner: "No Dockerfile found"

**Решение:**
- В Railway → Settings → Root Directory должно быть: `runner`

---

## 📞 Поддержка

- Vercel Docs: https://vercel.com/docs
- Railway Docs: https://docs.railway.app
- Telegram Bot API: https://core.telegram.org/bots/api

---

**Удачи! 🚀**
