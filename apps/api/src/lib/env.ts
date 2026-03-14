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
});

export const env = envSchema.parse(process.env);
