import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { eq } from "drizzle-orm";
import { db, users, userPreferences } from "@autokindler/db";
import { authMiddleware } from "../middleware/auth.js";

const updateUserSchema = z.object({
  kindle_email: z.string().email("Must be a valid email").optional(),
  preferences: z
    .object({
      max_papers_per_month: z
        .number()
        .int()
        .min(1)
        .max(100)
        .optional(),
      category_scores: z
        .record(z.string(), z.number().min(1).max(10))
        .optional(),
    })
    .optional(),
});

export const userRoutes = new Hono();

// Apply auth middleware to all user routes
userRoutes.use("*", authMiddleware);

// GET /api/users/me — retrieve user profile + preferences
userRoutes.get("/me", async (c) => {
  const userId = c.get("userId") as string;

  const result = await db
    .select({
      id: users.id,
      email: users.email,
      kindleEmail: users.kindleEmail,
      categoryScores: userPreferences.categoryScores,
      maxPapersPerMonth: userPreferences.maxPapersPerMonth,
    })
    .from(users)
    .leftJoin(userPreferences, eq(users.id, userPreferences.userId))
    .where(eq(users.id, userId))
    .limit(1);

  if (result.length === 0) {
    return c.json({ success: false, error: "User not found" }, 404);
  }

  const row = result[0];
  return c.json({
    success: true,
    data: {
      id: row.id,
      email: row.email,
      kindle_email: row.kindleEmail,
      preferences: {
        max_papers_per_month: row.maxPapersPerMonth ?? 30,
        category_scores: (row.categoryScores as Record<string, number>) ?? {},
      },
    },
  });
});

// PUT /api/users/me — update kindle email and/or preferences
userRoutes.put(
  "/me",
  zValidator("json", updateUserSchema, (result, c) => {
    if (!result.success) {
      return c.json(
        {
          success: false,
          error: result.error.issues.map((i) => i.message).join("; "),
        },
        400
      );
    }
  }),
  async (c) => {
    const userId = c.get("userId") as string;

    const body = c.req.valid("json");

    // Verify user exists
    const existing = await db
      .select({ id: users.id })
      .from(users)
      .where(eq(users.id, userId))
      .limit(1);

    if (existing.length === 0) {
      return c.json({ success: false, error: "User not found" }, 404);
    }

    // Update kindle_email if provided
    if (body.kindle_email) {
      await db
        .update(users)
        .set({ kindleEmail: body.kindle_email })
        .where(eq(users.id, userId));
    }

    // Upsert preferences if provided
    if (body.preferences) {
      const updateFields: Record<string, unknown> = {
        updatedAt: new Date(),
      };
      if (body.preferences.max_papers_per_month !== undefined) {
        updateFields.maxPapersPerMonth = body.preferences.max_papers_per_month;
      }
      if (body.preferences.category_scores !== undefined) {
        updateFields.categoryScores = body.preferences.category_scores;
      }

      await db
        .insert(userPreferences)
        .values({
          userId,
          ...(body.preferences.max_papers_per_month !== undefined && {
            maxPapersPerMonth: body.preferences.max_papers_per_month,
          }),
          ...(body.preferences.category_scores !== undefined && {
            categoryScores: body.preferences.category_scores,
          }),
        })
        .onConflictDoUpdate({
          target: userPreferences.userId,
          set: updateFields,
        });
    }

    return c.json({
      success: true,
      data: { message: "Preferences updated successfully." },
    });
  }
);
