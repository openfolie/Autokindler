import { z } from "zod";

const envSchema = z.object({
  DATABASE_URL: z
    .string()
    .default("postgres://autokindler:autokindler@localhost:5432/autokindler"),
  SQS_ENDPOINT: z.string().default("http://localhost:4566"),
  SQS_QUEUE_URL: z
    .string()
    .default(
      "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/autokindler-deliveries"
    ),
  AWS_REGION: z.string().default("us-east-1"),
  PORT: z.coerce.number().default(3000),

  // GitHub OAuth
  GITHUB_CLIENT_ID: z.string().default(""),
  GITHUB_CLIENT_SECRET: z.string().default(""),

  // JWT
  JWT_SECRET: z
    .string()
    .min(32, "JWT_SECRET must be at least 32 characters")
    .default("dev-secret-change-me-in-production-at-least-32-chars"),
  JWT_EXPIRY: z.string().default("7d"),

  // App URL (used for OAuth callback redirect)
  APP_URL: z.string().url().default("http://localhost:3000"),
});

export const env = envSchema.parse(process.env);
