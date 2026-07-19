export default function QuickStartPage() {
  const steps = [
    {
      num: 1,
      title: '📝 Регистрация на GitHub',
      url: 'https://github.com/signup',
      desc: 'Создайте аккаунт на GitHub (бесплатно)',
      time: '2 мин',
    },
    {
      num: 2,
      title: '☁️ Регистрация на Vercel',
      url: 'https://vercel.com/signup',
      desc: 'Войдите через GitHub (бесплатно)',
      time: '1 мин',
    },
    {
      num: 3,
      title: '🚂 Регистрация на Railway',
      url: 'https://railway.app',
      desc: 'Войдите через GitHub ($5 trial бесплатно)',
      time: '1 мин',
    },
    {
      num: 4,
      title: '🗄️ Создание PostgreSQL на Railway',
      url: 'https://railway.app',
      desc: 'New Project → Database → Add PostgreSQL',
      time: '2 мин',
    },
    {
      num: 5,
      title: '🤖 Создание Telegram-бота',
      url: 'https://t.me/BotFather',
      desc: 'Отправьте /newbot в @BotFather, получите токен',
      time: '2 мин',
    },
    {
      num: 6,
      title: '🆔 Получение Telegram ID',
      url: 'https://t.me/userinfobot',
      desc: 'Узнайте свой ID через @userinfobot',
      time: '1 мин',
    },
    {
      num: 7,
      title: '🔑 API credentials',
      url: 'https://my.telegram.org',
      desc: 'Получите api_id и api_hash для отслеживания подарков',
      time: '3 мин',
    },
    {
      num: 8,
      title: '🌐 Деплой сайта на Vercel',
      url: 'https://vercel.com/new',
      desc: 'Импорт GitHub репозитория + 5 переменных',
      time: '5 мин',
    },
    {
      num: 9,
      title: '🗃️ Применение схемы БД',
      url: '#',
      desc: 'npx drizzle-kit push (создаст таблицы)',
      time: '2 мин',
    },
    {
      num: 10,
      title: '🚀 Деплой Runner на Railway',
      url: 'https://railway.app',
      desc: 'New Service → GitHub Repo → Root Directory: runner',
      time: '5 мин',
    },
    {
      num: 11,
      title: '🔗 Связать сайт и runner',
      url: 'https://vercel.com',
      desc: 'Обновить RUNNER_URL в Vercel, сделать Redeploy',
      time: '3 мин',
    },
    {
      num: 12,
      title: '✅ Проверка и настройка админа',
      url: '#',
      desc: 'SQL запрос: UPDATE users SET is_admin=true',
      time: '2 мин',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        🚀 Упрощённая установка
      </h1>
      <p className="text-slate-400 mb-8">
        Только 3 сервиса: GitHub + Vercel + Railway
      </p>

      {/* Статистика */}
      <div className="grid md:grid-cols-4 gap-4 mb-10">
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Сервисов</p>
          <p className="text-3xl font-bold text-blue-400">3</p>
        </div>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Время</p>
          <p className="text-3xl font-bold text-cyan-400">~30 мин</p>
        </div>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Стоимость</p>
          <p className="text-3xl font-bold text-green-400">$5/мес</p>
        </div>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Сложность</p>
          <p className="text-3xl font-bold text-purple-400">Легко</p>
        </div>
      </div>

      {/* Архитектура */}
      <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 mb-8">
        <h3 className="text-xl font-bold mb-4">🏗️ Архитектура</h3>
        <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-sm overflow-x-auto">
{`┌───────────────┐
│    GitHub     │  ← Код проекта (бесплатно)
└───────────────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌───────────────┐  ┌───────────────┐
│    Vercel     │  │   Railway     │
│    (сайт)     │  │ (БД + runner) │
│   бесплатно   │  │   $5/мес      │
└───────────────┘  └───────────────┘`}
        </pre>
      </div>

      {/* Шаги */}
      <div className="space-y-3">
        {steps.map((step) => (
          <a
            key={step.num}
            href={step.url === '#' ? undefined : step.url}
            target={step.url === '#' ? undefined : '_blank'}
            className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-5 hover:border-blue-500/50 transition"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-xl font-bold flex-shrink-0">
                {step.num}
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-lg font-bold">{step.title}</h3>
                  <span className="text-xs text-slate-400">{step.time}</span>
                </div>
                <p className="text-sm text-slate-400">{step.desc}</p>
              </div>
            </div>
          </a>
        ))}
      </div>

      {/* Важные переменные */}
      <div className="mt-10 bg-gradient-to-r from-yellow-900/30 to-orange-900/30 border border-yellow-500/30 rounded-xl p-6">
        <h3 className="text-xl font-bold mb-4">🔑 Переменные окружения</h3>
        
        <h4 className="font-semibold mt-4 mb-2">Vercel (сайт):</h4>
        <div className="space-y-1 text-sm font-mono">
          <Var name="DATABASE_URL" desc="Публичный URL из Railway" />
          <Var name="ADMIN_TELEGRAM_ID" desc="Ваш Telegram ID" />
          <Var name="RUNNER_SECRET" desc="Придумайте сами" />
          <Var name="BOT_USERNAME" desc="@username бота" />
          <Var name="RUNNER_URL" desc="URL runner'а из Railway" />
        </div>

        <h4 className="font-semibold mt-4 mb-2">Railway (runner):</h4>
        <div className="space-y-1 text-sm font-mono">
          <Var name="BOT_TOKEN" desc="От @BotFather" />
          <Var name="OWNER_TELEGRAM_ID" desc="Ваш ID" />
          <Var name="OWNER_PHONE" desc="+7..." />
          <Var name="OWNER_API_ID" desc="С my.telegram.org" />
          <Var name="OWNER_API_HASH" desc="С my.telegram.org" />
          <Var name="WEBSITE_URL" desc="URL сайта с Vercel" />
          <Var name="RUNNER_SECRET" desc="ТОТ ЖЕ что на Vercel!" />
        </div>
      </div>

      {/* CTA */}
      <div className="mt-10 grid md:grid-cols-3 gap-4">
        <a
          href="https://github.com"
          target="_blank"
          className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-center hover:border-blue-500/50 transition"
        >
          <div className="text-3xl mb-2">📝</div>
          <div className="font-bold">GitHub</div>
          <div className="text-sm text-slate-400">github.com</div>
        </a>
        <a
          href="https://vercel.com"
          target="_blank"
          className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-center hover:border-blue-500/50 transition"
        >
          <div className="text-3xl mb-2">☁️</div>
          <div className="font-bold">Vercel</div>
          <div className="text-sm text-slate-400">vercel.com</div>
        </a>
        <a
          href="https://railway.app"
          target="_blank"
          className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-center hover:border-blue-500/50 transition"
        >
          <div className="text-3xl mb-2">🚂</div>
          <div className="font-bold">Railway</div>
          <div className="text-sm text-slate-400">railway.app</div>
        </a>
      </div>

      {/* Итого */}
      <div className="mt-10 bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/30 rounded-xl p-6 text-center">
        <h3 className="text-2xl font-bold mb-2">🎉 Итого: $5/месяц</h3>
        <p className="text-slate-300">
          GitHub ($0) + Vercel ($0) + Railway ($5) = рабочий BotHost
        </p>
      </div>
    </div>
  );
}

function Var({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="flex items-center gap-3 py-1 border-b border-blue-900/20 last:border-0">
      <span className="text-cyan-300">{name}</span>
      <span className="text-slate-500">—</span>
      <span className="text-slate-400">{desc}</span>
    </div>
  );
}
