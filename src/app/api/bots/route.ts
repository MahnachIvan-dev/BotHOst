import { NextRequest, NextResponse } from 'next/server';
import { validateBotCode } from '@/lib/validate-bot';
import { createBot, getUserBots, getOrCreateUser } from '@/lib/db-operations';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { telegramId, username, filename, code } = body;

    if (!telegramId || !filename || !code) {
      return NextResponse.json({ error: 'Отсутствуют обязательные поля' }, { status: 400 });
    }

    // Валидация кода
    const validation = validateBotCode(code);
    if (!validation.valid) {
      return NextResponse.json(
        {
          error: 'Код не прошёл валидацию',
          details: validation.errors,
          warnings: validation.warnings,
        },
        { status: 400 }
      );
    }

    // Получаем или создаём пользователя
    const user = await getOrCreateUser(telegramId, username);

    // Создаём бота
    const bot = await createBot(user.id, filename, code);

    return NextResponse.json({
      success: true,
      bot,
      warnings: validation.warnings,
      detectedLibraries: validation.detectedLibraries,
    });
  } catch (error: any) {
    console.error('Upload error:', error);
    return NextResponse.json({ error: error.message || 'Ошибка при загрузке' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const telegramId = request.nextUrl.searchParams.get('telegramId');
    if (!telegramId) {
      return NextResponse.json({ error: 'telegramId required' }, { status: 400 });
    }

    const user = await getOrCreateUser(telegramId);
    const bots = await getUserBots(user.id);

    return NextResponse.json({ bots });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
