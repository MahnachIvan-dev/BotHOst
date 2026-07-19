import { NextRequest, NextResponse } from 'next/server';
import {
  getUserActiveSubscriptions,
  createSubscription,
  getOrCreateUser,
} from '@/lib/db-operations';
import { PLANS, PlanId } from '@/lib/constants';

export async function GET(request: NextRequest) {
  try {
    const telegramId = request.nextUrl.searchParams.get('telegramId');
    if (!telegramId) {
      return NextResponse.json({ error: 'telegramId required' }, { status: 400 });
    }

    const user = await getOrCreateUser(telegramId);
    const subscriptions = await getUserActiveSubscriptions(user.id);

    return NextResponse.json({ subscriptions });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// Этот endpoint только для промокодов и внутренних операций бота
// Реальная оплата Stars происходит через Telegram Bot API
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { telegramId, username, planId, confirmed } = body;

    if (!telegramId || !planId) {
      return NextResponse.json({ error: 'Отсутствуют обязательные поля' }, { status: 400 });
    }

    const plan = PLANS[planId as PlanId];
    if (!plan) {
      return NextResponse.json({ error: 'Неверный план' }, { status: 400 });
    }

    const user = await getOrCreateUser(telegramId, username);

    // Реальная оплата должна подтверждаться Telegram Bot API
    // confirmed флаг выставляется после оплаты в боте
    if (confirmed) {
      const sub = await createSubscription(user.id, plan.id, plan.days);
      return NextResponse.json({ success: true, subscription: sub, plan });
    }

    // Возвращаем информацию о плане для отображения в боте
    return NextResponse.json({
      success: true,
      plan,
      paymentRequired: true,
      instructions: `Для оплаты ${plan.stars} звёзд откройте Telegram-бота и используйте команду /buy ${plan.id}`,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
