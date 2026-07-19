import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'BotHost — Хостинг Telegram-ботов',
  description: 'Хостинг ваших Telegram-ботов с оплатой через Telegram Stars',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 min-h-screen text-slate-100 antialiased">
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-blue-900/40 backdrop-blur-sm bg-slate-950/70 sticky top-0 z-40">
            <nav className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2 group">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-xl shadow-lg shadow-blue-500/30">
                  🤖
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                  BotHost
                </span>
              </a>
              <div className="flex items-center gap-6 text-sm">
                <a href="/#pricing" className="hover:text-blue-400 transition">Тарифы</a>
                <a href="/upload" className="hover:text-blue-400 transition">Загрузить</a>
                <a href="/dashboard" className="hover:text-blue-400 transition">Кабинет</a>
                <a href="/quickstart" className="hover:text-blue-400 transition">📚 Установка</a>
              </div>
            </nav>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-blue-900/40 bg-slate-950/70 mt-16">
            <div className="max-w-7xl mx-auto px-6 py-8 text-center text-sm text-slate-400">
              <p>© 2026 BotHost — хостинг Telegram-ботов с оплатой через Telegram Stars</p>
              <p className="mt-2 text-xs">Токены ботов не указываются в коде — подставляются автоматически из переменных окружения</p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
