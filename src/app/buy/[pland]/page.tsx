import { notFound } from 'next/navigation';
import { PLANS, PlanId } from '@/lib/constants';

export default function BuyPage({ params }: { params: Promise<{ planId: string }> }) {
  // Используем синхронный доступ через params (Next.js 16)
  return <BuyPageInner planId={(params as any).planId} />;
}

function BuyPageInner({ planId }: { planId: string }) {
  const plan = PLANS[planId as PlanId];
  if (!plan) notFound();

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        Оплата через Telegram Stars
      </h1>

      <div className="bg-slate-900/40 border border-blue-900/40 rounded-2xl p-8 mb-6">
        <h2 className="text-2xl font-bold mb-4">{plan.name}</h2>
        <ul className="space-y-2 text-slate-300 mb-6">
          <li>✓ {plan.description}</li>
          <li>✓ Длительность: {plan.duration}</li>
          <li>✓ Поддержка 24/7</li>
        </ul>
        <div className="flex items-baseline gap-2 mb-6">
          <span className="text-5xl font-bold bg-gradient-to-r from-yellow-300 to-orange-400 bg-clip-text text-transparent">
            {plan.stars}
          </span>
          <span className="text-slate-400 text-xl">⭐ Telegram Stars</span>
        </div>

        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6">
          <p className="text-blue-200 text-sm">
            💡 Оплата проходит <strong>только через Telegram-бота</strong>. Звёзды поступают напрямую владельцу, минуя посредников.
          </p>
        </div>

        <a
          href="https://t.me/YourBotHostBot"
          target="_blank"
          className="block text-center py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold shadow-lg shadow-blue-500/20 text-lg"
        >
          📱 Открыть бота для оплаты
        </a>

        <p className="text-center text-xs text-slate-400 mt-4">
          В боте отправьте команду <code className="bg-slate-950 px-2 py-0.5 rounded">/buy {plan.id}</code> или выберите тариф в меню
        </p>
      </div>

      <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-sm text-slate-300">
        <h3 className="font-bold mb-2">Как это работает?</h3>
        <ol className="list-decimal ml-5 space-y-1">
          <li>Откройте Telegram-бота по ссылке выше</li>
          <li>Выберите тариф <strong>{plan.name}</strong></li>
          <li>Подтвердите оплату {plan.stars} звёзд</li>
          <li>Слот активируется автоматически на {plan.duration}</li>
          <li>Загружайте бота через сайт или через самого бота</li>
        </ol>
      </div>
    </div>
  );
}
