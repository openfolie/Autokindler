import type { MiddlewareHandler } from "hono";

interface RateLimitEntry {
  timestamps: number[];
}

/**
 * In-memory sliding window rate limiter.
 * Tracks requests per authenticated user (from JWT via c.get('userId')).
 * Must run AFTER auth middleware in the middleware chain.
 */
export function rateLimiter(opts: {
  windowMs: number;
  max: number;
}): MiddlewareHandler {
  const store = new Map<string, RateLimitEntry>();

  return async (c, next) => {
    const userId = c.get("userId") as string | undefined;
    if (!userId) {
      // If no user ID, skip rate limiting (auth middleware will reject anyway)
      return next();
    }

    const now = Date.now();
    const windowStart = now - opts.windowMs;

    // Get or create entry
    let entry = store.get(userId);
    if (!entry) {
      entry = { timestamps: [] };
      store.set(userId, entry);
    }

    // Clean up expired timestamps
    entry.timestamps = entry.timestamps.filter((ts) => ts > windowStart);

    // Check limit
    if (entry.timestamps.length >= opts.max) {
      return c.json(
        {
          success: false,
          error: `Rate limit exceeded. Maximum ${opts.max} delivery requests per hour.`,
        },
        429,
      );
    }

    // Record this request
    entry.timestamps.push(now);

    // Periodic cleanup of stale entries (every 100th request)
    if (Math.random() < 0.01) {
      for (const [key, val] of store.entries()) {
        val.timestamps = val.timestamps.filter((ts) => ts > windowStart);
        if (val.timestamps.length === 0) {
          store.delete(key);
        }
      }
    }

    return next();
  };
}
