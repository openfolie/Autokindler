import type { MiddlewareHandler } from "hono";
import { getCookie } from "hono/cookie";
import { verifyJwt } from "../lib/jwt.js";

/**
 * Hono middleware that verifies JWT from Authorization header or cookie.
 * On success: sets userId and userEmail on Hono context.
 * On failure: returns 401 Unauthorized.
 */
export const authMiddleware: MiddlewareHandler = async (c, next) => {
  let token: string | undefined;

  // 1. Check Authorization: Bearer <token> header
  const authHeader = c.req.header("Authorization");
  if (authHeader?.startsWith("Bearer ")) {
    token = authHeader.slice(7);
  }

  // 2. Fallback: check autokindler_token cookie
  if (!token) {
    token = getCookie(c, "autokindler_token");
  }

  if (!token) {
    return c.json({ success: false, error: "Unauthorized" }, 401);
  }

  try {
    const payload = await verifyJwt(token);

    if (!payload.sub || !payload.email) {
      return c.json({ success: false, error: "Unauthorized" }, 401);
    }

    // Set user info on Hono context
    c.set("userId", payload.sub);
    c.set("userEmail", payload.email);

    return next();
  } catch {
    return c.json({ success: false, error: "Unauthorized" }, 401);
  }
};
