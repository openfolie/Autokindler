"""MessageQueue interface and DeliveryTask data model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DeliveryTask:
    """A delivery job received from the queue."""

    delivery_id: str
    url: str
    kindle_email: str
    receipt_handle: str


class MessageQueue(ABC):
    """Abstract interface for a message queue backend."""

    @abstractmethod
    def poll(self, max_messages: int = 1) -> list[DeliveryTask]:
        """Long-poll for delivery tasks.

        Returns an empty list if no messages are available within the
        wait window.
        """

    @abstractmethod
    def ack(self, receipt_handle: str) -> None:
        """Acknowledge (delete) a successfully processed message."""
