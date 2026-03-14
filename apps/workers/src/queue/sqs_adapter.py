"""SQS implementation of the MessageQueue interface."""

from __future__ import annotations

import json

import boto3
import structlog

from .interface import DeliveryTask, MessageQueue

log = structlog.get_logger()


class SQSQueue(MessageQueue):
    """Amazon SQS (or LocalStack) message queue adapter."""

    def __init__(
        self,
        queue_url: str,
        endpoint_url: str,
        region: str = "us-east-1",
    ) -> None:
        self._queue_url = queue_url
        # Use dummy credentials for LocalStack
        extra_kwargs: dict = {}
        if "localhost" in endpoint_url or "localstack" in endpoint_url:
            extra_kwargs.update(
                aws_access_key_id="test",
                aws_secret_access_key="test",
            )
        self._client = boto3.client(
            "sqs",
            endpoint_url=endpoint_url,
            region_name=region,
            **extra_kwargs,
        )

    def poll(self, max_messages: int = 1) -> list[DeliveryTask]:
        """Long-poll SQS for up to *max_messages* delivery tasks."""
        resp = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20,
        )
        messages = resp.get("Messages", [])
        tasks: list[DeliveryTask] = []
        for msg in messages:
            try:
                body = json.loads(msg["Body"])
                tasks.append(
                    DeliveryTask(
                        delivery_id=body["deliveryId"],
                        url=body["url"],
                        kindle_email=body["kindleEmail"],
                        receipt_handle=msg["ReceiptHandle"],
                    )
                )
            except (json.JSONDecodeError, KeyError) as exc:
                log.error(
                    "invalid_sqs_message",
                    message_id=msg.get("MessageId"),
                    error=str(exc),
                )
                # ACK malformed messages so they don't loop forever
                self._client.delete_message(
                    QueueUrl=self._queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
        return tasks

    def ack(self, receipt_handle: str) -> None:
        """Delete a processed message from SQS."""
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle,
        )
