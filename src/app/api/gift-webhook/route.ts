import { NextRequest, NextResponse } from 'next/server';
import { createSubscription, getOrCreateUser, createPayment } from '@/lib/db-operations';
import { PLANS, PlanId } from '@/lib/constants';

/**
 * Endpoint для обработки уведомлений о подарках от runner'а.
 * Runner отслеживает подарки через Userbot и уведомляет сайт.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { secret, senderId, senderUsername, giftId, giftValue, giftName } = body;

    // Проверка секрета runner'а
    const runnerSecret = process.env.RUNNER_SECRET;
    if (!runnerSecret || secret !== runnerSecret) {
      return NextResponse.json({ error: 'Invalid secret' }, { status: 403 });
    }

    if (!senderId || !giftId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Определяем план по стоимости подарка
    let planId: PlanId;
    if (giftValue >= 50) {
      planId = 'month';
    } else if (giftValue >= 25) {
      planId = '2weeks';
    } else if (giftValue >= 15) {
      planId = 'week';
    } else {
      return NextResponse.json(
        { error: 'Gift value too low (minimum 15 stars)' },
        { status: 400 }
      );
    }

    const plan = PLANS[planId];

    // Получаем/создаём пользователя
    const user = await getOrCreateUser(String(senderId), senderUsername);

    // Создаём подписку
    const subscription = await createSubscription(user.id, planId, plan.days);

    // Сохраняем платёж (как подарок)
    await createPayment(
      user.id,
      giftValue,
      planId,
      `gift:${giftId}:${giftName || 'unknown'}`
    );

    return NextResponse.json({
      success: true,
      subscription,
      plan,
      message: `Activated ${plan.name} for user ${senderId}`,
    });
  } catch (error: any) {
    console.error('Gift webhook error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
