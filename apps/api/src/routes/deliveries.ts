import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { eq, and } from "drizzle-orm";
import { db, users, deliveryLog } from "@autokindler/db";
import { enqueueDelivery } from "../lib/sqs.js";

const arxivUrlPattern =
  /^https?:\/\/arxiv\.org\/(abs|html|pdf)\/\d{4}\.\d{4,5}(v\d+)?(\.pdf)?$/;

const createDeliverySchema = z.object({
  url: z
    .string()
    .url("Must be a valid URL")
    .refine((url) => arxivUrlPattern.test(url), {
      message:
        "URL must be a valid arXiv paper link (e.g. https://arxiv.org/html/2401.12345v1)",
    }),
});

const uuidSchema = z.string().uuid();

export const deliveryRoutes = new Hono();

// POST /api/deliveries — create a new delivery
deliveryRoutes.post(
  "/",
  zValidator("json", createDeliverySchema, (result, c) => {
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
    const userId = c.req.header("X-User-Id");
    if (!userId) {
      return c.json(
        { success: false, error: "Missing X-User-Id header" },
        401
      );
    }

    const { url } = c.req.valid("json");

    // Look up user to get kindle_email
    const user = await db
      .select({ id: users.id, kindleEmail: users.kindleEmail })
      .from(users)
      .where(eq(users.id, userId))
      .limit(1);

    if (user.length === 0) {
      return c.json({ success: false, error: "User not found" }, 404);
    }

    if (!user[0].kindleEmail) {
      return c.json(
        {
          success: false,
          error: "Kindle email not configured. Please set it in your profile.",
        },
        400
      );
    }

    // Insert into delivery_log — unique constraint catches duplicates
    try {
      const [delivery] = await db
        .insert(deliveryLog)
        .values({
          userId,
          sourceUrl: url,
          status: "Pending",
        })
        .returning({ id: deliveryLog.id, status: deliveryLog.status });

      // Enqueue to SQS
      await enqueueDelivery({
        deliveryId: delivery.id,
        url,
        kindleEmail: user[0].kindleEmail,
      });

      return c.json(
        {
          success: true,
          data: {
            delivery_id: delivery.id,
            status: delivery.status,
          },
        },
        202
      );
    } catch (err: unknown) {
      // Check for unique constraint violation (duplicate delivery)
      const pgError = err as { code?: string };
      if (pgError.code === "23505") {
        return c.json(
          { success: false, error: "Paper already submitted" },
          409
        );
      }
      throw err;
    }
  }
);

// GET /api/deliveries/:id — check delivery status
deliveryRoutes.get("/:id", async (c) => {
  const { id } = c.req.param();
  const userId = c.req.header("X-User-Id");

  if (!userId) {
    return c.json(
      { success: false, error: "Missing X-User-Id header" },
      401
    );
  }

  // Validate UUID format
  const parsed = uuidSchema.safeParse(id);
  if (!parsed.success) {
    return c.json({ success: false, error: "Invalid delivery ID format" }, 400);
  }

  const result = await db
    .select({
      id: deliveryLog.id,
      status: deliveryLog.status,
      errorMessage: deliveryLog.errorMessage,
      updatedAt: deliveryLog.updatedAt,
    })
    .from(deliveryLog)
    .where(and(eq(deliveryLog.id, id), eq(deliveryLog.userId, userId)))
    .limit(1);

  if (result.length === 0) {
    return c.json({ success: false, error: "Delivery not found" }, 404);
  }

  return c.json({
    success: true,
    data: {
      delivery_id: result[0].id,
      status: result[0].status,
      error_message: result[0].errorMessage,
      updated_at: result[0].updatedAt,
    },
  });
});
