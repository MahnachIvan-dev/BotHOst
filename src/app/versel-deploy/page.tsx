export default function VercelDeployPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        Деплой сайта на Vercel
      </h1>
      <p className="text-slate-400 mb-8">
        Упрощённая инструкция: Vercel + Railway (БД + runner)
      </p>

      {/* Шаги */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">1</span>
          Создайте БД на Railway
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <ol className="list-decimal ml-5 space-y-2 text-slate-300">
            <li>Откройте <a href="https://railway.app" target="_blank" className="text-blue-400">railway.app</a></li>
            <li>Нажмите <strong>+ New Project</strong></li>
            <li>Выберите <strong>Database → Add PostgreSQL</strong></li>
            <li>Подождите 1-2 минуты</li>
            <li>Откройте созданную БД → вкладка <strong>Connect</strong></li>
            <li>Найдите <strong>Public Network</strong> и скопируйте URL</li>
          </ol>
          <CodeBlock>{`postgresql://postgres:xxxxx@monorail.proxy.rlwy.net:12345/railway`}</CodeBlock>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">2</span>
          Загрузите код на GitHub
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <CodeBlock>{`# На вашем компьютере:
cd bothost
git add .
git commit -m "Initial commit"
git push -u origin main`}</CodeBlock>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">3</span>
          Импортируйте проект в Vercel
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <ol className="list-decimal ml-5 space-y-2 text-slate-300">
            <li>Откройте <a href="https://vercel.com/new" target="_blank" className="text-blue-400">vercel.com/new</a></li>
            <li>Найдите репозиторий <strong>bothost</strong></li>
            <li>Нажмите <strong>Import</strong></li>
            <li>Framework Preset: <strong>Next.js</strong> (определится автоматически)</li>
          </ol>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">4</span>
          Добавьте переменные окружения
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <p className="text-slate-300">В Vercel → <strong>Environment Variables</strong> добавьте:</p>
          <div className="space-y-2">
            <VarBlock name="DATABASE_URL" value="postgresql://postgres:xxx@monorail.proxy.rlwy.net:12345/railway" />
            <VarBlock name="ADMIN_TELEGRAM_ID" value="5291847362" />
            <VarBlock name="RUNNER_SECRET" value="mysupersecret123" />
            <VarBlock name="BOT_USERNAME" value="MyBotHost_bot" />
            <VarBlock name="RUNNER_URL" value="https://runner.up.railway.app (обновим позже)" />
          </div>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">5</span>
          Нажмите Deploy
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <p className="text-slate-300">Подождите 2-3 минуты и получите URL сайта:</p>
          <CodeBlock>{`https://bothost-xxxx.vercel.app`}</CodeBlock>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">6</span>
          Примените схему БД
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <p className="text-slate-300">На вашем компьютере:</p>
          <CodeBlock>{`cd bothost
echo "DATABASE_URL=postgresql://..." > .env
npm install
npx drizzle-kit push`}</CodeBlock>
          <p className="text-slate-300">Это создаст все таблицы в БД.</p>
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm">7</span>
          Проверка
        </h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 space-y-3">
          <p className="text-slate-300">Откройте:</p>
          <CodeBlock>{`https://bothost-xxxx.vercel.app/api/health
# Должно показать: {"ok":true}`}</CodeBlock>
        </div>
      </section>

      <div className="bg-gradient-to-r from-blue-900/40 to-cyan-900/40 border border-blue-500/30 rounded-xl p-6">
        <h3 className="text-xl font-bold mb-2">✅ Готово!</h3>
        <p className="text-slate-300">
          Теперь задеплойте runner-сервер на Railway (см. <a href="/quickstart" className="text-blue-400">упрощённую инструкцию</a>).
        </p>
      </div>
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-sm overflow-x-auto font-mono text-slate-300">
      {children}
    </pre>
  );
}

function VarBlock({ name, value }: { name: string; value: string }) {
  return (
    <div className="bg-slate-950 border border-blue-900/50 rounded-lg p-3 font-mono text-sm">
      <span className="text-cyan-300">{name}</span>
      <span className="text-slate-500"> = </span>
      <span className="text-slate-300">{value}</span>
    </div>
  );
}
