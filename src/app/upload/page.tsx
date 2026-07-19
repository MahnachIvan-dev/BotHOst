'use client';

import { useState } from 'react';

export default function UploadPage() {
  const [telegramId, setTelegramId] = useState('');
  const [username, setUsername] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleFile = async (f: File) => {
    setFile(f);
    const text = await f.text();
    setCode(text);
  };

  const handleUpload = async () => {
    setError('');
    setResult(null);

    if (!telegramId.trim()) {
      setError('Укажите Telegram ID');
      return;
    }
    if (!code.trim()) {
      setError('Загрузите файл бота или вставьте код');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/bots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telegramId: telegramId.trim(),
          username: username.trim() || undefined,
          filename: file?.name || 'bot.py',
          code,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error + (data.details ? ': ' + data.details.join('; ') : ''));
      } else {
        setResult(data);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
        Загрузить Telegram-бота
      </h1>
      <p className="text-slate-400 mb-8">
        Загрузите Python-файл вашего Telegram-бота. Токен указывать в коде НЕ нужно — он будет подставлен автоматически.
      </p>

      {/* Инфо-бокс про токен */}
      <div className="mb-8 bg-blue-900/20 border border-blue-500/30 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <span>🔑</span> Как получать токен в коде
        </h3>
        <p className="text-slate-300 text-sm mb-3">
          Используйте <code className="bg-slate-900 px-2 py-0.5 rounded">os.environ.get(&quot;BOT_TOKEN&quot;)</code> или{' '}
          <code className="bg-slate-900 px-2 py-0.5 rounded">os.getenv(&quot;BOT_TOKEN&quot;)</code>
        </p>
        <pre className="bg-slate-950 border border-blue-900/50 rounded-lg p-4 text-sm overflow-x-auto">
{`import os
from aiogram import Bot, Dispatcher

# ✅ ПРАВИЛЬНО — токен берётся из окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()`}
        </pre>
      </div>

      <div className="bg-slate-900/40 border border-blue-900/40 rounded-2xl p-6 space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Telegram ID *</label>
            <input
              type="text"
              value={telegramId}
              onChange={(e) => setTelegramId(e.target.value)}
              placeholder="123456789"
              className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg focus:border-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="@username"
              className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg focus:border-blue-500 outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Python-файл бота *</label>
          <input
            type="file"
            accept=".py"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg file:mr-4 file:py-1 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-500 file:cursor-pointer"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Или вставьте код вручную</label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            rows={12}
            placeholder="# Вставьте код бота здесь..."
            className="w-full px-4 py-2 bg-slate-950 border border-blue-900/50 rounded-lg font-mono text-sm focus:border-blue-500 outline-none"
          />
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4 text-red-200">
            <strong>❌ Ошибка:</strong> {error}
          </div>
        )}

        {result && (
          <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4">
            <strong className="text-green-300">✅ Бот успешно загружен!</strong>
            <p className="text-sm text-slate-300 mt-2">
              ID бота: {result.bot.id}, файл: {result.bot.filename}
            </p>
            {result.warnings?.length > 0 && (
              <div className="mt-3 text-yellow-300 text-sm">
                <strong>⚠️ Предупреждения:</strong>
                <ul className="list-disc ml-5 mt-1">
                  {result.warnings.map((w: string, i: number) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.detectedLibraries?.length > 0 && (
              <p className="text-sm text-slate-300 mt-2">
                Обнаруженные библиотеки: {result.detectedLibraries.join(', ')}
              </p>
            )}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-lg font-semibold disabled:opacity-50 transition-all shadow-lg shadow-blue-500/20"
        >
          {loading ? '⏳ Загрузка и проверка...' : '🚀 Загрузить и проверить'}
        </button>
      </div>

      <div className="mt-6 text-center text-slate-400 text-sm">
        💡 Удобнее загружать через Telegram-бот?{' '}
        <a
          href="https://t.me/YourBotHostBot"
          target="_blank"
          className="text-blue-400 hover:text-blue-300 underline"
        >
          Откройте @YourBotHostBot
        </a>
      </div>
    </div>
  );
}
