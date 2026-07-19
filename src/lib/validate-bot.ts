import { TELEGRAM_LIBRARIES, TOKEN_PATTERNS } from './constants';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  detectedLibraries: string[];
}

/**
 * Проверяет, является ли загруженный Python-код именно Telegram-ботом,
 * а не обычным скриптом. Токены должны браться из окружения, а не хардкодиться.
 */
export function validateBotCode(code: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const detectedLibraries: string[] = [];

  if (!code || code.trim().length === 0) {
    errors.push('Файл пустой');
    return { valid: false, errors, warnings, detectedLibraries };
  }

  if (code.length > 200_000) {
    errors.push('Файл слишком большой (максимум 200 КБ)');
    return { valid: false, errors, warnings, detectedLibraries };
  }

  // 1. Проверка на наличие Telegram-библиотек
  const lowerCode = code.toLowerCase();
  for (const lib of TELEGRAM_LIBRARIES) {
    const regex = new RegExp(`(import\\s+${lib}|from\\s+${lib}\\s+import)`, 'i');
    if (regex.test(code)) {
      detectedLibraries.push(lib);
    }
  }

  if (detectedLibraries.length === 0) {
    errors.push(
      'Не обнаружены импорты Telegram-библиотек (aiogram, telebot, pyrogram, python-telegram-bot и др.). Это должен быть именно Telegram-бот.'
    );
  }

  // 2. Проверка на запуск бота (dispatcher, executor, run_polling и т.д.)
  const runnerPatterns = [
    /dp\.run_polling/i,
    /executor\.start_polling/i,
    /app\.run_polling/i,
    /bot\.run_forever/i,
    /bot\.polling/i,
    /updater\.start_polling/i,
    /client\.run/i,
    /asyncio\.run.*main/i,
    /if __name__\s*==\s*["']__main__["']/,
  ];

  const hasRunner = runnerPatterns.some((p) => p.test(code));
  if (!hasRunner && detectedLibraries.length > 0) {
    warnings.push(
      'Не найден явный запуск бота (run_polling, start_polling, executor и т.д.). Убедитесь, что бот корректно стартует.'
    );
  }

  // 3. Проверка на хардкоднутые токены
  for (const pattern of TOKEN_PATTERNS) {
    const matches = code.match(pattern);
    if (matches && matches.length > 0) {
      errors.push(
        'Обнаружен хардкоднутый токен в коде. Используйте os.environ.get("BOT_TOKEN") или os.getenv("BOT_TOKEN") — токен будет подставлен автоматически.'
      );
      break;
    }
  }

  // 4. Проверка, что токен берётся из окружения
  const envPatterns = [
    /os\.environ\.get\s*\(\s*["']BOT_TOKEN["']/,
    /os\.getenv\s*\(\s*["']BOT_TOKEN["']/,
    /os\.environ\s*\[\s*["']BOT_TOKEN["']\s*\]/,
    /environ\[["']BOT_TOKEN["']\]/,
    /getenv\s*\(\s*["']BOT_TOKEN["']/,
  ];

  const usesEnvToken = envPatterns.some((p) => p.test(code));
  if (!usesEnvToken && detectedLibraries.length > 0) {
    warnings.push(
      'Рекомендуем получать токен через os.environ.get("BOT_TOKEN") — система автоматически подставит его при запуске.'
    );
  }

  // 5. Проверка на опасные операции
  const dangerousPatterns = [
    /subprocess\.(call|Popen|run)\s*\(\s*["']rm\s+/i,
    /os\.system\s*\(\s*["']rm\s+/i,
    /shutil\.rmtree/i,
    /os\.remove\s*\(\s*["']\//,
    /open\s*\(\s*["']\/etc\//i,
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(code)) {
      errors.push('Обнаружены потенциально опасные операции с файловой системой.');
      break;
    }
  }

  // 6. Проверка на синтаксис (базовая — на уровне парных скобок)
  const openParens = (code.match(/\(/g) || []).length;
  const closeParens = (code.match(/\)/g) || []).length;
  if (openParens !== closeParens) {
    errors.push('Нарушен баланс круглых скобок — возможно, синтаксическая ошибка.');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    detectedLibraries,
  };
}
