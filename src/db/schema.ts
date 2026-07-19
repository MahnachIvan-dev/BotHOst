import { pgTable, serial, text, integer, timestamp, boolean, varchar } from 'drizzle-orm/pg-core';

// Таблица пользователей
export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  telegramId: varchar('telegram_id', { length: 255 }).unique().notNull(),
  username: varchar('username', { length: 255 }),
  isAdmin: boolean('is_admin').default(false),
  starsBalance: integer('stars_balance').default(0),
  createdAt: timestamp('created_at').defaultNow(),
});

// Таблица ботов
export const bots = pgTable('bots', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').references(() => users.id).notNull(),
  filename: varchar('filename', { length: 255 }).notNull(),
  code: text('code').notNull(),
  status: varchar('status', { length: 50 }).default('stopped'), // running, stopped, error
  errorMessage: text('error_message'),
  startedAt: timestamp('started_at'),
  stoppedAt: timestamp('stopped_at'),
  createdAt: timestamp('created_at').defaultNow(),
});

// Таблица подписок
export const subscriptions = pgTable('subscriptions', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').references(() => users.id).notNull(),
  botSlot: integer('bot_slot').notNull(), // номер слота
  plan: varchar('plan', { length: 50 }).notNull(), // week, 2weeks, month
  expiresAt: timestamp('expires_at').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
});

// Таблица промокодов
export const promoCodes = pgTable('promo_codes', {
  id: serial('id').primaryKey(),
  code: varchar('code', { length: 100 }).unique().notNull(),
  planType: varchar('plan_type', { length: 50 }).notNull(), // week, 2weeks, month
  usesLeft: integer('uses_left').notNull(),
  createdBy: integer('created_by').references(() => users.id),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow(),
});

// Таблица использований промокодов
export const promoUses = pgTable('promo_uses', {
  id: serial('id').primaryKey(),
  promoCodeId: integer('promo_code_id').references(() => promoCodes.id).notNull(),
  userId: integer('user_id').references(() => users.id).notNull(),
  usedAt: timestamp('used_at').defaultNow(),
});

// Таблица платежей (для истории)
export const payments = pgTable('payments', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').references(() => users.id).notNull(),
  amount: integer('amount').notNull(), // количество звёзд
  plan: varchar('plan', { length: 50 }).notNull(),
  telegramPaymentId: varchar('telegram_payment_id', { length: 255 }),
  createdAt: timestamp('created_at').defaultNow(),
});
