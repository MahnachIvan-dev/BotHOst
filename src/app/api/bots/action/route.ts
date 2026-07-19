import { NextRequest, NextResponse } from 'next/server';
import { getBotById, updateBotStatus, getOrCreateUser } from '@/lib/db-operations';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { botId, telegramId, action } = body;

    if (!botId || !telegramId || !action) {
      return NextResponse.json({ error: 'Отсутствуют обязательные поля' }, { status: 400 });
    }

    const user = await getOrCreateUser(telegramId);
    const bot = await getBotById(botId);

    if (!bot) {
      return NextResponse.json({ error: 'Бот не найден' }, { status: 404 });
    }

    if (bot.userId !== user.id) {
      return NextResponse.json({ error: 'Нет доступа к этому боту' }, { status: 403 });
    }

    if (action === 'start') {
      // В реальном приложении здесь должен быть вызов runner-сервиса,
      // который выполнит код Python-бота в изолированном окружении.
      // Здесь симулируем успешный запуск.
      await updateBotStatus(botId, 'running');
      return NextResponse.json({ success: true, status: 'running' });
    }

    if (action === 'stop') {
      await updateBotStatus(botId, 'stopped');
      return NextResponse.json({ success: true, status: 'stopped' });
    }

    if (action === 'delete') {
      await updateBotStatus(botId, 'stopped');
      const { deleteBot } = await import('@/lib/db-operations');
      await deleteBot(botId);
      return NextResponse.json({ success: true });
    }

    return NextResponse.json({ error: 'Неизвестное действие' }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
