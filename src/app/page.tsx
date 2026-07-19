import { PLANS } from '@/lib/constants';

export default function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-transparent to-cyan-600/10 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 py-20 relative">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-400 bg-clip-text text-transparent">
              Хостинг Telegram-ботов
            </h1>
            <p className="text-xl text-slate-300 mb-4">
              Загружайте и запускайте своих Telegram-ботов 24/7.
            </p>
            <p className="text-lg text-pink-300 mb-8">
              🎁 Оплата через <strong>Telegram Gifts</strong> — дарите подарки владельцу и получайте слот автоматически!
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              <a
                href="/upload"
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold shadow-lg shadow-blue-500/30 transition-all hover:shadow-xl hover:shadow-blue-500/40 hover:-translate-y-0.5"
              >
                🚀 Загрузить бота
              </a>
              <a
                href="#pricing"
                className="px-8 py-4 border-2 border-blue-500/50 hover:border-blue-400 rounded-lg font-semibold transition-all hover:bg-blue-500/10"
              >
                💎 Посмотреть тарифы
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">Возможности платформы</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon="🔒"
            title="Безопасность"
            description="Токены ботов не указываются в коде — автоматически подставляются из переменных окружения"
          />
          <FeatureCard
            icon="⚡"
            title="Быстрый старт"
            description="Загрузите Python-файл бота и запустите его за несколько минут"
          />
          <FeatureCard
            icon="🎁"
            title="Оплата подарками"
            description="Дарите подарки владельцу через Telegram — слот активируется автоматически"
          />
          <FeatureCard
            icon="🎁"
            title="Промокоды"
            description="Активируйте промокоды на бесплатные слоты для хостинга ботов"
          />
          <FeatureCard
            icon="📱"
            title="Telegram-бот"
            description="Управляйте ботами через удобный Telegram-интерфейс"
          />
          <FeatureCard
            icon="🛡️"
            title="Валидация кода"
            description="Система проверяет, что загружается именно Telegram-бот, а не обычный скрипт"
          />
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold text-center mb-4">Тарифы</h2>
        <p className="text-center text-slate-400 mb-12">
          Выберите подходящий тариф. Оплата только через Telegram Stars.
        </p>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {Object.values(PLANS).map((plan) => (
            <div
              key={plan.id}
              className="relative bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-blue-900/50 rounded-2xl p-8 backdrop-blur-sm hover:border-blue-500/50 transition-all hover:-translate-y-1"
            >
              {plan.id === 'month' && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-1 rounded-full text-xs font-semibold shadow-lg">
                  ВЫГОДНО
                </div>
              )}
              <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
              <p className="text-slate-400 text-sm mb-6">{plan.description}</p>
              <div className="mb-6">
                <span className="text-5xl font-bold bg-gradient-to-r from-yellow-300 to-orange-400 bg-clip-text text-transparent">
                  {plan.stars}
                </span>
                <span className="text-slate-400 ml-2">⭐</span>
              </div>
              <ul className="space-y-2 mb-6 text-sm">
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  Длительность: {plan.duration}
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  Слотов: {plan.slots}
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  Поддержка 24/7
                </li>
              </ul>
              <a
                href={`/buy/${plan.id}`}
                className="block text-center py-3 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold transition-all shadow-lg shadow-blue-500/20"
              >
                Купить
              </a>
            </div>
          ))}
        </div>

        {/* Промокод */}
        <div className="mt-12 max-w-2xl mx-auto bg-gradient-to-r from-purple-900/40 to-blue-900/40 border border-purple-500/30 rounded-2xl p-8 text-center">
          <h3 className="text-2xl font-bold mb-2">🎁 Есть промокод?</h3>
          <p className="text-slate-300 mb-4">
            Активируйте его в Telegram-боте или в личном кабинете для получения бесплатного слота
          </p>
          <a
            href="/dashboard"
            className="inline-block px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 rounded-lg font-semibold transition-all"
          >
            Активировать промокод
          </a>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-4xl font-bold text-center mb-12">Как это работает</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <StepCard number={1} title="Выберите тариф" description="Оплатите слот через Telegram Stars" />
          <StepCard number={2} title="Загрузите код" description="Python-файл вашего Telegram-бота" />
          <StepCard number={3} title="Проверка кода" description="Система проверит, что это именно бот" />
          <StepCard number={4} title="Запуск" description="Бот запустится и будет работать 24/7" />
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 backdrop-blur-sm hover:border-blue-500/40 transition-all">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm">{description}</p>
    </div>
  );
}

function StepCard({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-2xl font-bold shadow-lg shadow-blue-500/30">
        {number}
      </div>
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm">{description}</p>
    </div>
  );
}
