// Планы подписок
export const PLANS = {
  week: {
    id: 'week',
    name: 'Неделя',
    duration: '7 дней',
    stars: 15,
    days: 7,
    slots: 1,
    description: '1 слот для бота на 7 дней',
  },
  '2weeks': {
    id: '2weeks',
    name: '2 недели',
    duration: '14 дней',
    stars: 25,
    days: 14,
    slots: 1,
    description: '1 слот для бота на 14 дней',
  },
  month: {
    id: 'month',
    name: 'Месяц',
    duration: '30 дней',
    stars: 50,
    days: 30,
    slots: 1,
    description: '1 слот для бота на 30 дней',
  },
} as const;

export type PlanId = keyof typeof PLANS;

// Telegram-библиотеки, которые должны быть импортированы в коде бота
export const TELEGRAM_LIBRARIES = [
  'aiogram',
  'telebot',
  'pyTelegramBotAPI',
  'telegram',
  'python-telegram-bot',
  'pyrogram',
  'telethon',
  'grammy',
  'telegraf',
  'botogram',
];

// Регулярки для поиска хардкоднутых токенов
export const TOKEN_PATTERNS = [
  /\d{8,10}:[A-Za-z0-9_-]{35}/g, // стандартный формат Telegram Bot Token
  /bot[_-]?token\s*=\s*["'][^"']+["']/gi,
  /token\s*=\s*["'][0-9]{8,10}:[A-Za-z0-9_-]{35}["']/g,
  /API_KEY\s*=\s*["'][^"']+["']/gi,
  /SECRET\s*=\s*["'][^"']+["']/gi,
];

// Ссылка на Telegram бота (заменить на реальный)
export const BOT_USERNAME = 'YourBotHostBot';
export const BOT_LINK = `https://t.me/${BOT_USERNAME}`;
