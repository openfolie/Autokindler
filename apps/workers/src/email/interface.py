"""EmailSender interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Abstract interface for sending emails with attachments."""

    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_path: str,
        attachment_filename: str,
    ) -> None:
        """Send an email with a single file attachment."""
