import { defineConfig } from "drizzle-kit";

const DATABASE_URL =
  process.env.DATABASE_URL ??
  "postgres://autokindler:autokindler@localhost:5432/autokindler";

export default defineConfig({
  dialect: "postgresql",
  schema: "./src/schema.ts",
  dbCredentials: {
    url: DATABASE_URL,
  },
  out: "./drizzle",
});
