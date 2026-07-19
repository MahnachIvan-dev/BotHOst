import Link from 'next/link';

export default function InstallPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        📚 Полная инструкция по установке
      </h1>
      <p className="text-slate-400 mb-8">
        Пошаговое руководство для полных новичков — от регистрации до работающего проекта
      </p>

      {/* Quick stats */}
      <div className="grid md:grid-cols-3 gap-4 mb-10">
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Время установки</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            ~2 часа
          </p>
        </div>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Стоимость</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            $5/мес
          </p>
        </div>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <p className="text-slate-400 text-sm">Сложность</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            Для новичков
          </p>
        </div>
      </div>

      {/* Warning box */}
      <div className="bg-gradient-to-r from-yellow-900/30 to-orange-900/30 border border-yellow-500/30 rounded-xl p-6 mb-8">
        <h3 className="text-xl font-bold mb-2">⚠️ Важно</h3>
        <p className="text-slate-300 text-sm">
          Эта страница — краткая версия инструкции. Полная пошаговая инструкция со скриншотами и подробными объяснениями 
          находится в файле <code className="bg-slate-950 px-2 py-0.5 rounded">INSTALL.md</code> в корне проекта.
        </p>
      </div>

      {/* Шаги */}
      <div className="space-y-4">
        <StepCard 
          num={1} 
          title="Регистрация на сервисах"
          desc="GitHub, Vercel, Neon (БД), Railway"
          details={[
            "GitHub — для хранения кода",
            "Vercel — бесплатный хостинг сайта",
            "Neon — бесплатная PostgreSQL база",
            "Railway — для runner-сервера"
          ]}
        />
        <StepCard 
          num={2} 
          title="Установка программ"
          desc="Git, Node.js, Python 3.11, VSCode, Vercel CLI"
          details={[
            "Git — система контроля версий",
            "Node.js — для работы Next.js",
            "Python 3.11 — для runner'а",
            "VSCode — редактор кода"
          ]}
        />
        <StepCard 
          num={3} 
          title="Создание Telegram-бота"
          desc="Через @BotFather получаем токен"
          details={[
            "Открыть @BotFather",
            "Команда /newbot",
            "Придумать имя и username",
            "Сохранить токен"
          ]}
        />
        <StepCard 
          num={4} 
          title="Получение Telegram ID"
          desc="Через @userinfobot"
          details={[
            "Открыть @userinfobot",
            "Нажать Start",
            "Получить свой ID",
            "Это OWNER_TELEGRAM_ID"
          ]}
        />
        <StepCard 
          num={5} 
          title="API credentials (для подарков)"
          desc="Через my.telegram.org"
          details={[
            "Зайти под номером владельца",
            "API development tools",
            "Create application",
            "Сохранить api_id и api_hash"
          ]}
        />
        <StepCard 
          num={6} 
          title="Создание БД на Neon"
          desc="Бесплатная PostgreSQL"
          details={[
            "Create Project",
            "Выбрать регион",
            "Скопировать строку подключения",
            "Это DATABASE_URL"
          ]}
        />
        <StepCard 
          num={7} 
          title="Деплой сайта на Vercel"
          desc="Импорт с GitHub + переменные"
          details={[
            "Import Git Repository",
            "Добавить 5 переменных окружения",
            "Нажать Deploy",
            "Подождать 2-3 минуты"
          ]}
        />
        <StepCard 
          num={8} 
          title="Применение схемы БД"
          desc="Создание таблиц"
          details={[
            "npx drizzle-kit push",
            "Создаст 6 таблиц",
            "users, bots, subscriptions",
            "promo_codes, promo_uses, payments"
          ]}
        />
        <StepCard 
          num={9} 
          title="Деплой Runner на Railway"
          desc="Сервер запускающий ботов"
          details={[
            "Deploy from GitHub",
            "Root Directory: runner",
            "Добавить 8 переменных",
            "Сгенерировать домен"
          ]}
        />
        <StepCard 
          num={10} 
          title="Обновление RUNNER_URL"
          desc="Связать сайт и runner"
          details={[
            "Скопировать URL runner'а",
            "Добавить в Vercel",
            "Сделать Redeploy",
            "Проверить /api/health"
          ]}
        />
        <StepCard 
          num={11} 
          title="Настройка админа"
          desc="SQL запрос в Neon"
          details={[
            "Открыть SQL Editor",
            "UPDATE users SET is_admin=true",
            "WHERE telegram_id='ВАШ_ID'",
            "Теперь вы админ!"
          ]}
        />
        <StepCard 
          num={12} 
          title="Проверка работы"
          desc="Финальное тестирование"
          details={[
            "Сайт открывается?",
            "/api/health → ok:true?",
            "Бот отвечает в Telegram?",
            "Тестовый подарок активировал слот?"
          ]}
        />
      </div>

      {/* CTA */}
      <div className="mt-12 bg-gradient-to-r from-blue-900/40 to-cyan-900/40 border border-blue-500/30 rounded-2xl p-8 text-center">
        <h2 className="text-3xl font-bold mb-4">🚀 Готовы начать?</h2>
        <p className="text-slate-300 mb-6">
          Откройте файл <code className="bg-slate-950 px-2 py-1 rounded">INSTALL.md</code> в корне проекта
          для подробной пошаговой инструкции
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <a
            href="https://github.com"
            target="_blank"
            className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg font-semibold transition"
          >
            📝 GitHub (регистрация)
          </a>
          <a
            href="https://vercel.com"
            target="_blank"
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold transition"
          >
            ☁️ Vercel (деплой сайта)
          </a>
          <a
            href="https://railway.app"
            target="_blank"
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-semibold transition"
          >
            🚂 Railway (деплой runner)
          </a>
          <a
            href="https://neon.tech"
            target="_blank"
            className="px-6 py-3 bg-green-600 hover:bg-green-500 rounded-lg font-semibold transition"
          >
            🗄️ Neon (база данных)
          </a>
        </div>
      </div>

      {/* Быстрые ссылки */}
      <div className="mt-8 grid md:grid-cols-2 gap-4">
        <Link
          href="/vercel-deploy"
          className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 hover:border-blue-500/50 transition"
        >
          <h3 className="text-xl font-bold mb-2">🌐 Деплой на Vercel</h3>
          <p className="text-slate-400 text-sm">
            Краткая инструкция по деплою сайта на Vercel
          </p>
        </Link>
        <Link
          href="/bot-setup"
          className="block bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 hover:border-blue-500/50 transition"
        >
          <h3 className="text-xl font-bold mb-2">🤖 Telegram-бот</h3>
          <p className="text-slate-400 text-sm">
            Код бота + инструкция по запуску
          </p>
        </Link>
      </div>
    </div>
  );
}

function StepCard({ num, title, desc, details }: { num: number; title: string; desc: string; details: string[] }) {
  return (
    <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 hover:border-blue-500/40 transition">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-xl font-bold flex-shrink-0">
          {num}
        </div>
        <div className="flex-1">
          <h3 className="text-xl font-bold mb-1">{title}</h3>
          <p className="text-slate-400 text-sm mb-3">{desc}</p>
          <ul className="grid md:grid-cols-2 gap-1">
            {details.map((d, i) => (
              <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                <span className="text-green-400">✓</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
