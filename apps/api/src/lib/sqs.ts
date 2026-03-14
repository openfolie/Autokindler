import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";
import { env } from "./env.js";

const sqsClient = new SQSClient({
  region: env.AWS_REGION,
  endpoint: env.SQS_ENDPOINT,
  // LocalStack doesn't need real credentials
  ...(env.SQS_ENDPOINT.includes("localhost") && {
    credentials: {
      accessKeyId: "test",
      secretAccessKey: "test",
    },
  }),
});

export interface DeliveryMessage {
  deliveryId: string;
  url: string;
  kindleEmail: string;
}

export async function enqueueDelivery(payload: DeliveryMessage): Promise<void> {
  const command = new SendMessageCommand({
    QueueUrl: env.SQS_QUEUE_URL,
    MessageBody: JSON.stringify(payload),
  });

  await sqsClient.send(command);
}
