"""SES SMTP implementation of the EmailSender interface."""

from __future__ import annotations

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import structlog

from .interface import EmailSender

log = structlog.get_logger()


class SESEmailSender(EmailSender):
    """Send emails via Amazon SES SMTP (or LocalStack)."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        timeout: int = 30,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._from_email = from_email
        self._timeout = timeout

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_path: str,
        attachment_filename: str,
    ) -> None:
        """Build and send a MIME email with an attachment."""
        msg = MIMEMultipart()
        msg["From"] = self._from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach file
        file_path = Path(attachment_path)
        with file_path.open("rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment_filename}"',
        )
        msg.attach(part)

        # Send via SMTP
        log.info(
            "sending_email",
            to=to_email,
            subject=subject,
            attachment=attachment_filename,
        )
        use_auth = bool(self._smtp_user)
        with smtplib.SMTP(
            self._smtp_host, self._smtp_port, timeout=self._timeout
        ) as server:
            if use_auth:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
            server.sendmail(self._from_email, [to_email], msg.as_string())
        log.info("email_sent", to=to_email)
