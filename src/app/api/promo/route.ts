import { NextRequest, NextResponse } from 'next/server';
import { usePromoCode, getOrCreateUser } from '@/lib/db-operations';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { telegramId, username, code } = body;

    if (!telegramId || !code) {
      return NextResponse.json({ error: 'Отсутствуют обязательные поля' }, { status: 400 });
    }

    const user = await getOrCreateUser(telegramId, username);
    const result = await usePromoCode(user.id, code);

    if (!result.success) {
      return NextResponse.json({ error: result.message }, { status: 400 });
    }

    return NextResponse.json({
      success: true,
      message: result.message,
      planType: result.planType,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
