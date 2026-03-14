import {
  pgTable,
  uuid,
  varchar,
  boolean,
  timestamp,
  jsonb,
  integer,
  text,
  uniqueIndex,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

// ─── Users ───────────────────────────────────────────────────────────────────

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: varchar("email", { length: 255 }).unique().notNull(),
  kindleEmail: varchar("kindle_email", { length: 255 }).unique(),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
});

// ─── User Preferences ────────────────────────────────────────────────────────

export const userPreferences = pgTable("user_preferences", {
  userId: uuid("user_id")
    .primaryKey()
    .references(() => users.id, { onDelete: "cascade" }),
  categoryScores: jsonb("category_scores").default("{}"),
  maxPapersPerMonth: integer("max_papers_per_month").default(30),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// ─── Daily Papers (Cache) ────────────────────────────────────────────────────

export const dailyPapers = pgTable("daily_papers", {
  arxivId: varchar("arxiv_id", { length: 20 }).primaryKey(),
  title: text("title").notNull(),
  categories: jsonb("categories").notNull(),
  huggingfaceRank: integer("huggingface_rank"),
  fetchedAt: timestamp("fetched_at").defaultNow(),
});

// ─── Delivery Log ────────────────────────────────────────────────────────────

export const deliveryLog = pgTable(
  "delivery_log",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    sourceUrl: varchar("source_url", { length: 500 }).notNull(),
    status: varchar("status", { length: 20 }).notNull().default("Pending"),
    errorMessage: text("error_message"),
    createdAt: timestamp("created_at").defaultNow(),
    updatedAt: timestamp("updated_at").defaultNow(),
  },
  (table) => [
    uniqueIndex("delivery_user_url_idx").on(table.userId, table.sourceUrl),
  ]
);

// ─── Relations ───────────────────────────────────────────────────────────────

export const usersRelations = relations(users, ({ one, many }) => ({
  preferences: one(userPreferences, {
    fields: [users.id],
    references: [userPreferences.userId],
  }),
  deliveries: many(deliveryLog),
}));

export const userPreferencesRelations = relations(
  userPreferences,
  ({ one }) => ({
    user: one(users, {
      fields: [userPreferences.userId],
      references: [users.id],
    }),
  })
);

export const deliveryLogRelations = relations(deliveryLog, ({ one }) => ({
  user: one(users, {
    fields: [deliveryLog.userId],
    references: [users.id],
  }),
}));
