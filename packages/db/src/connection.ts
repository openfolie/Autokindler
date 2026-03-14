import postgres from "postgres";
import { drizzle } from "drizzle-orm/postgres-js";
import * as schema from "./schema.js";

const DATABASE_URL =
  process.env.DATABASE_URL ??
  "postgres://autokindler:autokindler@localhost:5432/autokindler";

export const client = postgres(DATABASE_URL, { max: 10 });

export const db = drizzle(client, { schema });
