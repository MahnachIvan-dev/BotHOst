'use client';

import { useState, useEffect } from 'react';

type Section = 'stats' | 'users' | 'bots' | 'subscriptions' | 'promos' | 'payments';

export default function AdminPage() {
  const [adminId, setAdminId] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [section, setSection] = useState<Section>('stats');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Форма создания промокода
  const [newPromo, setNewPromo] = useState({ code: '', planType: 'week', usesLeft: 1 });
  const [promoMessage, setPromoMessage] = useState('');

  useEffect(() => {
    const saved = localStorage.getItem('adminId');
    if (saved) {
      setAdminId(saved);
      setAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (authenticated) loadSection(section);
  }, [authenticated, section]);

  const login = async () => {
    if (!adminId.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/admin?section=stats&adminId=${adminId.trim()}`);
      if (!res.ok) {
        alert('Недостаточно прав. Убедитесь, что ваш Telegram ID добавлен как админ.');
        setLoading(false);
        return;
      }
      localStorage.setItem('adminId', adminId.trim());
      setAuthenticated(true);
    } catch (e) {
      alert('Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  const loadSection = async (s: Section) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/admin?section=${s}&adminId=${adminId}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const adminAction = async (action: string, extra: Record<string, any>) => {
    const res = await fetch(`/api/admin?adminId=${adminId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-admin-telegram-id': adminId },
      body: JSON.stringify({ action, ...extra }),
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.error || 'Ошибка');
      return;
    }
    loadSection(section);
  };

  const createPromo = async () => {
    if (!newPromo.code.trim()) return;
    const res = await fetch(`/api/admin?adminId=${adminId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-admin-telegram-id': adminId },
      body: JSON.stringify({
        action: 'createPromo',
        code: newPromo.code.toUpperCase(),
        planType: newPromo.planType,
        usesLeft: newPromo.usesLeft,
      }),
    });
    const json = await res.json();
    if (res.ok) {
      setPromoMessage('✅ Промокод создан');
      setNewPromo({ code: '', planType: 'week', usesLeft: 1 });
      loadSection('promos');
    } else {
      setPromoMessage('❌ ' + json.error);
    }
  };

  if (!authenticated) {
    return (
      <div className="max-w-md mx-auto px-6 py-20">
        <h1 className="text-3xl font-bold mb-6 text-center">🔐 Вход в админ-панель</h1>
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-2xl p-6 space-y-4">
          <input
            type="text"
            value={adminId}
            onChange={(e) => setAdminId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && login()}
            placeholder="Ваш Telegram ID (должен быть в админах)"
            className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg focus:border-blue-500 outline-none"
          />
          <button
            onClick={login}
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-red-600 to-orange-500 hover:from-red-500 hover:to-orange-400 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? 'Проверка...' : 'Войти как админ'}
          </button>
          <p className="text-xs text-slate-400 text-center">
            Для получения прав администратора обратитесь к владельцу или выполните в БД:<br />
            <code className="bg-slate-950 px-2 py-1 rounded">UPDATE users SET is_admin=true WHERE telegram_id=&apos;ВАШ_ID&apos;</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">
          🔐 Админ-панель
        </h1>
        <button
          onClick={() => {
            localStorage.removeItem('adminId');
            setAuthenticated(false);
          }}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm"
        >
          Выйти
        </button>
      </div>

      {/* Навигация */}
      <div className="flex flex-wrap gap-2 mb-6">
        {(['stats', 'users', 'bots', 'subscriptions', 'promos', 'payments'] as Section[]).map((s) => (
          <button
            key={s}
            onClick={() => setSection(s)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              section === s
                ? 'bg-gradient-to-r from-red-600 to-orange-500 text-white'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            {
              {
                stats: '📊 Статистика',
                users: '👥 Пользователи',
                bots: '🤖 Боты',
                subscriptions: '💳 Подписки',
                promos: '🎁 Промокоды',
                payments: '💰 Платежи',
              }[s]
            }
          </button>
        ))}
      </div>

      {loading && <p className="text-slate-400">Загрузка...</p>}

      {/* Статистика */}
      {section === 'stats' && data?.stats && (
        <div className="grid md:grid-cols-5 gap-4">
          <StatCard label="Пользователей" value={data.stats.totalUsers} icon="👥" />
          <StatCard label="Всего ботов" value={data.stats.totalBots} icon="🤖" />
          <StatCard label="Работает сейчас" value={data.stats.runningBots} icon="▶️" />
          <StatCard label="Активных подписок" value={data.stats.activeSubscriptions} icon="💳" />
          <StatCard label="Всего звёзд" value={data.stats.totalRevenue} icon="⭐" />
        </div>
      )}

      {/* Пользователи */}
      {section === 'users' && data?.users && (
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-950">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Telegram</th>
                <th className="text-left px-4 py-3">Username</th>
                <th className="text-left px-4 py-3">Админ</th>
                <th className="text-left px-4 py-3">Дата</th>
                <th className="text-left px-4 py-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              {data.users.map((u: any) => (
                <tr key={u.id} className="border-t border-blue-900/20">
                  <td className="px-4 py-3">{u.id}</td>
                  <td className="px-4 py-3 font-mono">{u.telegramId}</td>
                  <td className="px-4 py-3">{u.username || '—'}</td>
                  <td className="px-4 py-3">
                    {u.isAdmin ? <span className="text-green-400">✓</span> : <span className="text-slate-500">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(u.createdAt).toLocaleDateString('ru-RU')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => adminAction('toggleAdmin', { userId: u.id, isAdmin: !u.isAdmin })}
                      className="px-3 py-1 bg-blue-600/80 hover:bg-blue-500 rounded text-xs"
                    >
                      {u.isAdmin ? 'Снять админа' : 'Сделать админом'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Боты */}
      {section === 'bots' && data?.bots && (
        <div className="space-y-2">
          {data.bots.map((b: any) => (
            <div key={b.id} className="bg-slate-900/40 border border-blue-900/40 rounded-lg p-4 flex items-center justify-between">
              <div>
                <div className="font-semibold">#{b.id} {b.filename}</div>
                <div className="text-xs text-slate-400">
                  User ID: {b.userId} • Status: <span className="text-blue-300">{b.status}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => adminAction('stopBot', { botId: b.id })}
                  className="px-3 py-1 bg-yellow-600/80 hover:bg-yellow-500 rounded text-xs"
                >
                  Стоп
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить бота?')) adminAction('deleteBot', { botId: b.id });
                  }}
                  className="px-3 py-1 bg-red-600/80 hover:bg-red-500 rounded text-xs"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Подписки */}
      {section === 'subscriptions' && data?.subscriptions && (
        <div className="space-y-2">
          {data.subscriptions.map((s: any) => (
            <div key={s.id} className="bg-slate-900/40 border border-blue-900/40 rounded-lg p-4 flex items-center justify-between">
              <div>
                <div className="font-semibold">Слот #{s.botSlot} — {s.plan}</div>
                <div className="text-xs text-slate-400">
                  User {s.userId} • до {new Date(s.expiresAt).toLocaleDateString('ru-RU')}
                </div>
              </div>
              <button
                onClick={() => {
                  if (confirm('Удалить подписку?')) adminAction('deleteSubscription', { subId: s.id });
                }}
                className="px-3 py-1 bg-red-600/80 hover:bg-red-500 rounded text-xs"
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Промокоды */}
      {section === 'promos' && (
        <div className="space-y-6">
          <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
            <h3 className="font-semibold mb-3">Создать промокод</h3>
            <div className="grid md:grid-cols-4 gap-2">
              <input
                type="text"
                value={newPromo.code}
                onChange={(e) => setNewPromo({ ...newPromo, code: e.target.value })}
                placeholder="КОД"
                className="px-3 py-2 bg-slate-950 border border-blue-900/50 rounded uppercase"
              />
              <select
                value={newPromo.planType}
                onChange={(e) => setNewPromo({ ...newPromo, planType: e.target.value })}
                className="px-3 py-2 bg-slate-950 border border-blue-900/50 rounded"
              >
                <option value="week">Неделя (7 дн)</option>
                <option value="2weeks">2 недели (14 дн)</option>
                <option value="month">Месяц (30 дн)</option>
              </select>
              <input
                type="number"
                value={newPromo.usesLeft}
                onChange={(e) => setNewPromo({ ...newPromo, usesLeft: Number(e.target.value) })}
                placeholder="Кол-во"
                min={1}
                className="px-3 py-2 bg-slate-950 border border-blue-900/50 rounded"
              />
              <button
                onClick={createPromo}
                className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 rounded font-semibold"
              >
                + Создать
              </button>
            </div>
            {promoMessage && <p className="text-sm mt-2">{promoMessage}</p>}
          </div>

          {data?.promos && (
            <div className="space-y-2">
              {data.promos.map((p: any) => (
                <div key={p.id} className="bg-slate-900/40 border border-blue-900/40 rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="font-mono font-bold text-green-300">{p.code}</div>
                    <div className="text-xs text-slate-400">
                      {p.planType} • осталось: {p.usesLeft} • {p.isActive ? '✅ активен' : '❌ выключен'}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm('Удалить промокод?')) adminAction('deletePromo', { promoId: p.id });
                    }}
                    className="px-3 py-1 bg-red-600/80 hover:bg-red-500 rounded text-xs"
                  >
                    Удалить
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Платежи */}
      {section === 'payments' && data?.payments && (
        <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-950">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">User</th>
                <th className="text-left px-4 py-3">Звёзд</th>
                <th className="text-left px-4 py-3">План</th>
                <th className="text-left px-4 py-3">Дата</th>
              </tr>
            </thead>
            <tbody>
              {data.payments.map((p: any) => (
                <tr key={p.id} className="border-t border-blue-900/20">
                  <td className="px-4 py-3">{p.id}</td>
                  <td className="px-4 py-3">{p.userId}</td>
                  <td className="px-4 py-3 text-yellow-300">⭐ {p.amount}</td>
                  <td className="px-4 py-3">{p.plan}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(p.createdAt).toLocaleString('ru-RU')}
                  </td>
                </tr>
              ))}
              {data.payments.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                    Платежей пока нет
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="bg-slate-900/40 border border-blue-900/40 rounded-xl p-6">
      <div className="text-2xl mb-2">{icon}</div>
      <p className="text-slate-400 text-sm">{label}</p>
      <p className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        {value}
      </p>
    </div>
  );
}
