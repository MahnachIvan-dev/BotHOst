import { db } from '@/db';
import { users, bots, subscriptions, promoCodes, promoUses, payments } from '@/db/schema';
import { eq, and, gt, desc, sql } from 'drizzle-orm';

// === USERS ===

export async function getOrCreateUser(telegramId: string, username?: string) {
  let [user] = await db.select().from(users).where(eq(users.telegramId, telegramId));

  if (!user) {
    [user] = await db
      .insert(users)
      .values({ telegramId, username })
      .returning();
  } else if (username && user.username !== username) {
    [user] = await db
      .update(users)
      .set({ username })
      .where(eq(users.id, user.id))
      .returning();
  }

  return user;
}

export async function getUserById(id: number) {
  const [user] = await db.select().from(users).where(eq(users.id, id));
  return user;
}

export async function getAllUsers() {
  return await db.select().from(users).orderBy(desc(users.createdAt));
}

export async function makeUserAdmin(userId: number, isAdmin: boolean) {
  return await db.update(users).set({ isAdmin }).where(eq(users.id, userId)).returning();
}

// === BOTS ===

export async function createBot(userId: number, filename: string, code: string) {
  // Проверяем, есть ли активная подписка у пользователя
  const activeSubs = await getUserActiveSubscriptions(userId);
  if (activeSubs.length === 0) {
    throw new Error('Нет активной подписки. Купите слот или используйте промокод.');
  }

  const [bot] = await db
    .insert(bots)
    .values({ userId, filename, code, status: 'stopped' })
    .returning();
  return bot;
}

export async function getUserBots(userId: number) {
  return await db.select().from(bots).where(eq(bots.userId, userId)).orderBy(desc(bots.createdAt));
}

export async function getAllBots() {
  return await db.select().from(bots).orderBy(desc(bots.createdAt));
}

export async function getBotById(id: number) {
  const [bot] = await db.select().from(bots).where(eq(bots.id, id));
  return bot;
}

export async function updateBotStatus(id: number, status: string, errorMessage?: string) {
  const updates: any = { status };
  if (status === 'running') updates.startedAt = new Date();
  if (status === 'stopped' || status === 'error') updates.stoppedAt = new Date();
  if (errorMessage !== undefined) updates.errorMessage = errorMessage;

  return await db.update(bots).set(updates).where(eq(bots.id, id)).returning();
}

export async function deleteBot(id: number) {
  return await db.delete(bots).where(eq(bots.id, id));
}

// === SUBSCRIPTIONS ===

export async function createSubscription(userId: number, plan: string, days: number) {
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + days);

  // Находим следующий свободный слот
  const userSubs = await db
    .select()
    .from(subscriptions)
    .where(and(eq(subscriptions.userId, userId), gt(subscriptions.expiresAt, new Date())));

  const usedSlots = new Set(userSubs.map((s) => s.botSlot));
  let slot = 1;
  while (usedSlots.has(slot)) slot++;

  const [sub] = await db
    .insert(subscriptions)
    .values({ userId, plan, botSlot: slot, expiresAt })
    .returning();
  return sub;
}

export async function getUserActiveSubscriptions(userId: number) {
  return await db
    .select()
    .from(subscriptions)
    .where(and(eq(subscriptions.userId, userId), gt(subscriptions.expiresAt, new Date())))
    .orderBy(desc(subscriptions.expiresAt));
}

export async function getAllSubscriptions() {
  return await db.select().from(subscriptions).orderBy(desc(subscriptions.createdAt));
}

export async function deleteSubscription(id: number) {
  return await db.delete(subscriptions).where(eq(subscriptions.id, id));
}

// === PROMO CODES ===

export async function createPromoCode(code: string, planType: string, usesLeft: number, createdBy?: number) {
  const [promo] = await db
    .insert(promoCodes)
    .values({ code: code.toUpperCase(), planType, usesLeft, createdBy })
    .returning();
  return promo;
}

export async function getAllPromoCodes() {
  return await db.select().from(promoCodes).orderBy(desc(promoCodes.createdAt));
}

export async function getPromoCodeByCode(code: string) {
  const [promo] = await db
    .select()
    .from(promoCodes)
    .where(and(eq(promoCodes.code, code.toUpperCase()), eq(promoCodes.isActive, true)));
  return promo;
}

export async function usePromoCode(userId: number, code: string): Promise<{ success: boolean; message: string; planType?: string }> {
  const promo = await getPromoCodeByCode(code);

  if (!promo) {
    return { success: false, message: 'Промокод не найден или неактивен' };
  }

  if (promo.usesLeft <= 0) {
    return { success: false, message: 'Лимит использований промокода исчерпан' };
  }

  // Проверяем, использовал ли этот пользователь уже этот промокод
  const existingUse = await db
    .select()
    .from(promoUses)
    .where(and(eq(promoUses.promoCodeId, promo.id), eq(promoUses.userId, userId)));

  if (existingUse.length > 0) {
    return { success: false, message: 'Вы уже использовали этот промокод' };
  }

  // Создаём подписку и списываем использование
  await createSubscription(userId, promo.planType, getDaysForPlan(promo.planType));

  await db.insert(promoUses).values({ promoCodeId: promo.id, userId });

  await db
    .update(promoCodes)
    .set({ usesLeft: promo.usesLeft - 1 })
    .where(eq(promoCodes.id, promo.id));

  return { success: true, message: 'Промокод успешно активирован!', planType: promo.planType };
}

export async function deletePromoCode(id: number) {
  return await db.delete(promoCodes).where(eq(promoCodes.id, id));
}

function getDaysForPlan(plan: string): number {
  switch (plan) {
    case 'week':
      return 7;
    case '2weeks':
      return 14;
    case 'month':
      return 30;
    default:
      return 7;
  }
}

// === PAYMENTS ===

export async function createPayment(userId: number, amount: number, plan: string, telegramPaymentId?: string) {
  const [payment] = await db
    .insert(payments)
    .values({ userId, amount, plan, telegramPaymentId })
    .returning();
  return payment;
}

export async function getAllPayments() {
  return await db.select().from(payments).orderBy(desc(payments.createdAt));
}

// === STATISTICS ===

export async function getStats() {
  const [userCount] = await db.select({ count: sql<number>`count(*)` }).from(users);
  const [botCount] = await db.select({ count: sql<number>`count(*)` }).from(bots);
  const [activeSubCount] = await db
    .select({ count: sql<number>`count(*)` })
    .from(subscriptions)
    .where(gt(subscriptions.expiresAt, new Date()));
  const [totalRevenue] = await db.select({ sum: sql<number>`coalesce(sum(amount), 0)` }).from(payments);
  const runningBots = await db.select().from(bots).where(eq(bots.status, 'running'));

  return {
    totalUsers: Number(userCount.count),
    totalBots: Number(botCount.count),
    activeSubscriptions: Number(activeSubCount.count),
    totalRevenue: Number(totalRevenue.sum),
    runningBots: runningBots.length,
  };
}
