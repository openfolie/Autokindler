#!/bin/bash
set -e

echo "Creating SQS queues..."

# Create DLQ first
awslocal sqs create-queue \
  --queue-name autokindler-deliveries-dlq

DLQ_ARN=$(awslocal sqs get-queue-attributes \
  --queue-url http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/autokindler-deliveries-dlq \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

# Create main queue with redrive policy pointing to DLQ
awslocal sqs create-queue \
  --queue-name autokindler-deliveries \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"${DLQ_ARN}\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}"

echo "SQS queues created successfully."
