import { NextRequest, NextResponse } from 'next/server';
import {
  getAllUsers,
  getAllBots,
  getAllSubscriptions,
  getAllPromoCodes,
  getAllPayments,
  getStats,
  makeUserAdmin,
  deleteBot,
  deleteSubscription,
  createPromoCode,
  deletePromoCode,
  updateBotStatus,
  getUserById,
  getOrCreateUser,
} from '@/lib/db-operations';

// Простая проверка админа (в проде заменить на Telegram Login Widget)
async function requireAdmin(request: NextRequest) {
  const adminId = request.headers.get('x-admin-telegram-id') ||
    request.nextUrl.searchParams.get('adminId');

  if (!adminId) return null;

  const user = await getOrCreateUser(adminId);
  if (!user.isAdmin) return null;
  return user;
}

export async function GET(request: NextRequest) {
  try {
    const admin = await requireAdmin(request);
    if (!admin) {
      return NextResponse.json({ error: 'Нет прав доступа' }, { status: 403 });
    }

    const section = request.nextUrl.searchParams.get('section') || 'stats';

    if (section === 'stats') {
      const stats = await getStats();
      return NextResponse.json({ stats });
    }
    if (section === 'users') {
      const users = await getAllUsers();
      return NextResponse.json({ users });
    }
    if (section === 'bots') {
      const bots = await getAllBots();
      return NextResponse.json({ bots });
    }
    if (section === 'subscriptions') {
      const subscriptions = await getAllSubscriptions();
      return NextResponse.json({ subscriptions });
    }
    if (section === 'promos') {
      const promos = await getAllPromoCodes();
      return NextResponse.json({ promos });
    }
    if (section === 'payments') {
      const payments = await getAllPayments();
      return NextResponse.json({ payments });
    }

    return NextResponse.json({ error: 'Unknown section' }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const admin = await requireAdmin(request);
    if (!admin) {
      return NextResponse.json({ error: 'Нет прав доступа' }, { status: 403 });
    }

    const body = await request.json();
    const { action } = body;

    if (action === 'toggleAdmin') {
      const { userId, isAdmin } = body;
      await makeUserAdmin(userId, isAdmin);
      return NextResponse.json({ success: true });
    }

    if (action === 'deleteBot') {
      await deleteBot(body.botId);
      return NextResponse.json({ success: true });
    }

    if (action === 'stopBot') {
      await updateBotStatus(body.botId, 'stopped');
      return NextResponse.json({ success: true });
    }

    if (action === 'deleteSubscription') {
      await deleteSubscription(body.subId);
      return NextResponse.json({ success: true });
    }

    if (action === 'createPromo') {
      const promo = await createPromoCode(
        body.code,
        body.planType,
        body.usesLeft,
        admin.id
      );
      return NextResponse.json({ success: true, promo });
    }

    if (action === 'deletePromo') {
      await deletePromoCode(body.promoId);
      return NextResponse.json({ success: true });
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
