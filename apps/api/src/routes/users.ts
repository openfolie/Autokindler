import { Hono } from "hono";

export const userRoutes = new Hono();

// Stub — implemented fully in Task 2
userRoutes.get("/me", (c) => {
  return c.json({ success: false, error: "Not implemented" }, 501);
});
