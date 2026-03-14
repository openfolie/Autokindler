import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { serve } from "@hono/node-server";
import { env } from "./lib/env.js";
import { authRoutes } from "./routes/auth.js";
import { deliveryRoutes } from "./routes/deliveries.js";
import { userRoutes } from "./routes/users.js";

const app = new Hono();

// Global middleware
app.use("*", cors());
app.use("*", logger());

// Health check (public)
app.get("/", (c) => c.json({ status: "ok" }));

// Auth routes (public — these ARE the auth mechanism)
app.route("/api/auth", authRoutes);

// Protected routes (auth middleware applied inside each router)
app.route("/api/deliveries", deliveryRoutes);
app.route("/api/users", userRoutes);

// Start server
console.log(`Starting Hono server on port ${env.PORT}...`);
serve({ fetch: app.fetch, port: env.PORT }, (info) => {
  console.log(`Server running at http://localhost:${info.port}`);
});

export default app;
