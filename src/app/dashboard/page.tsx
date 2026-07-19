'use client';

import { useState, useEffect } from 'react';
import { PLANS } from '@/lib/constants';

interface Bot {
  id: number;
  filename: string;
  status: string;
  errorMessage?: string | null;
  startedAt?: string | null;
  createdAt: string;
}

interface Subscription {
  id: number;
  botSlot: number;
  plan: string;
  expiresAt: string;
}

export default function DashboardPage() {
  const [telegramId, setTelegramId] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [bots, setBots] = useState<Bot[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [promoCode, setPromoCode] = useState('');
  const [promoMessage, setPromoMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    if (!telegramId) return;
    setLoading(true);
    try {
      const [botsRes, subsRes] = await Promise.all([
        fetch(`/api/bots?telegramId=${telegramId}`),
        fetch(`/api/subscriptions?telegramId=${telegramId}`),
      ]);
      const botsData = await botsRes.json();
      const subsData = await subsRes.json();
      setBots(botsData.bots || []);
      setSubscriptions(subsData.subscriptions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    if (!telegramId.trim()) return;
    setAuthenticated(true);
    localStorage.setItem('telegramId', telegramId.trim());
    loadData();
  };

  useEffect(() => {
    const saved = localStorage.getItem('telegramId');
    if (saved) {
      setTelegramId(saved);
      setAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (authenticated) loadData();
  }, [authenticated]);

  const activatePromo = async () => {
    if (!promoCode.trim()) return;
    setPromoMessage('');
    try {
      const res = await fetch('/api/promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegramId, code: promoCode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setPromoMessage('❌ ' + data.error);
      } else {
        setPromoMessage('✅ ' + data.message);
        setPromoCode('');
        loadData();
      }
    } catch (e: any) {
      setPromoMessage('❌ ' + e.message);
    }
  };

  const handleBotAction = async (botId: number, action: 'start' | 'stop' | 'delete') => {
    await fetch('/api/bots/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ botId, telegramId, action }),
    });
    loadData();
  };

  const logout = () => {
    localStorage.removeItem('telegramId');
    setAuthenticated(false);
    setTelegramId('');
    setBots([]);
    setSubscriptions([]);
  };

  if (!authenticated) {
    return (
      <div className="max-w-md mx-auto px-6 py-20">
        <h1 className="text-3xl font-bold mb-6 text-center bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
          Вход в личный кабинет
        </h1>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-2xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Ваш Telegram ID</label>
            <input
              type="text"
              value={telegramId}
              onChange={(e) => setTelegramId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && login()}
              placeholder="123456789"
              className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg focus:border-blue-500 outline-none"
            />
            <p className="text-xs text-slate-400 mt-1">
              Узнать свой ID можно у бота @userinfobot
            </p>
          </div>
          <button
            onClick={login}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold transition-all"
          >
            Войти
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
          Личный кабинет
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400">ID: {telegramId}</span>
          <button
            onClick={logout}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition"
          >
            Выйти
          </button>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Активные подписки" value={subscriptions.length} />
        <StatCard label="Загружено ботов" value={bots.length} />
        <StatCard
          label="Работает сейчас"
          value={bots.filter((b) => b.status === 'running').length}
        />
      </div>

      {/* Подписки */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Мои подписки</h2>
        {subscriptions.length === 0 ? (
          <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-center">
            <p className="text-slate-400 mb-4">У вас нет активных подписок</p>
            <a
              href="/#pricing"
              className="inline-block px-6 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg font-semibold"
            >
              Купить слот
            </a>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {subscriptions.map((sub) => (
              <div
                key={sub.id}
                className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold">Слот #{sub.botSlot}</span>
                  <span className="text-xs px-2 py-1 bg-green-500/20 text-green-300 rounded">
                    Активна
                  </span>
                </div>
                <p className="text-slate-400 text-sm">
                  План: {PLANS[sub.plan as keyof typeof PLANS]?.name || sub.plan}
                </p>
                <p className="text-slate-400 text-sm">
                  Действует до: {new Date(sub.expiresAt).toLocaleDateString('ru-RU')}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Промокод */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold mb-4">🎁 Активировать промокод</h2>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value)}
              placeholder="Введите промокод"
              className="flex-1 px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg focus:border-blue-500 outline-none uppercase"
            />
            <button
              onClick={activatePromo}
              className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 rounded-lg font-semibold transition"
            >
              Активировать
            </button>
          </div>
          {promoMessage && (
            <p className={`mt-3 text-sm ${promoMessage.startsWith('✅') ? 'text-green-300' : 'text-red-300'}`}>
              {promoMessage}
            </p>
          )}
        </div>
      </section>

      {/* Боты */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Мои боты</h2>
          <a
            href="/upload"
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg text-sm font-semibold"
          >
            + Загрузить нового
          </a>
        </div>
        {loading ? (
          <p className="text-slate-400">Загрузка...</p>
        ) : bots.length === 0 ? (
          <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6 text-center">
            <p className="text-slate-400">У вас нет загруженных ботов</p>
          </div>
        ) : (
          <div className="space-y-3">
            {bots.map((bot) => (
              <div
                key={bot.id}
                className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-4 flex items-center justify-between"
              >
                <div>
                  <div className="font-semibold flex items-center gap-2">
                    🤖 {bot.filename}
                    <StatusBadge status={bot.status} />
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Загружен: {new Date(bot.createdAt).toLocaleString('ru-RU')}
                    {bot.startedAt && ` • Запущен: ${new Date(bot.startedAt).toLocaleString('ru-RU')}`}
                  </p>
                  {bot.errorMessage && (
                    <p className="text-xs text-red-300 mt-1">Ошибка: {bot.errorMessage}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  {bot.status === 'running' ? (
                    <button
                      onClick={() => handleBotAction(bot.id, 'stop')}
                      className="px-3 py-1 bg-red-600/80 hover:bg-red-500 rounded text-sm"
                    >
                      Стоп
                    </button>
                  ) : (
                    <button
                      onClick={() => handleBotAction(bot.id, 'start')}
                      className="px-3 py-1 bg-green-600/80 hover:bg-green-500 rounded text-sm"
                    >
                      Старт
                    </button>
                  )}
                  <button
                    onClick={() => {
                      if (confirm('Удалить бота?')) handleBotAction(bot.id, 'delete');
                    }}
                    className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
      <p className="text-slate-400 text-sm">{label}</p>
      <p className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        {value}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: 'bg-green-500/20 text-green-300',
    stopped: 'bg-slate-500/20 text-slate-300',
    error: 'bg-red-500/20 text-red-300',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[status] || styles.stopped}`}>
      {status}
    </span>
  );
}
