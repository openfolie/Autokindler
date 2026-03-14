"""Worker entry point — long-polling main loop with graceful shutdown."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time

import structlog

from .cache.file_cache import FileCache
from .config import Settings
from .db import get_connection, update_delivery_status
from .email.ses_adapter import SESEmailSender
from .pipeline.orchestrator import process_delivery
from .queue.interface import DeliveryTask
from .queue.sqs_adapter import SQSQueue

log = structlog.get_logger()


def _configure_logging() -> None:
    """Set up structlog with JSON output and timestamps."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
    )


def process_task(
    task: DeliveryTask,
    *,
    settings: Settings,
    conn,
    email_sender: SESEmailSender,
    cache: FileCache,
) -> None:
    """Process a single delivery task through the full pipeline.

    Delegates to process_delivery which handles all error cases internally
    and NEVER raises. Status is always updated in the database.
    """
    process_delivery(
        task=task,
        cache=cache,
        email_sender=email_sender,
        db_conn=conn,
        settings=settings,
    )


def _cache_cleanup_loop(cache: FileCache, shutdown: threading.Event) -> None:
    """Run cache cleanup every hour until shutdown is signalled."""
    while not shutdown.is_set():
        try:
            deleted = cache.cleanup()
            if deleted:
                log.info("periodic_cache_cleanup", deleted=deleted)
        except Exception:
            log.exception("cache_cleanup_error")
        # Sleep in 1-second increments so we can react to shutdown quickly
        for _ in range(3600):
            if shutdown.is_set():
                return
            time.sleep(1)


def main() -> None:
    """Worker entry point."""
    _configure_logging()

    settings = Settings()
    log.info("worker_starting", sqs_queue=settings.SQS_QUEUE_URL)

    # Initialize infrastructure
    conn = get_connection(settings.DATABASE_URL)
    queue = SQSQueue(
        queue_url=settings.SQS_QUEUE_URL,
        endpoint_url=settings.SQS_ENDPOINT,
        region=settings.AWS_REGION,
    )
    email_sender = SESEmailSender(
        smtp_host=settings.SES_SMTP_HOST,
        smtp_port=settings.SES_SMTP_PORT,
        smtp_user=settings.SES_SMTP_USER,
        smtp_password=settings.SES_SMTP_PASSWORD,
        from_email=settings.SES_FROM_EMAIL,
        timeout=settings.EMAIL_TIMEOUT,
    )
    cache = FileCache(settings.CACHE_DIR, settings.CACHE_TTL_DAYS)

    # Graceful shutdown via signal handler
    shutdown = threading.Event()

    def _signal_handler(signum, frame):
        log.info("shutdown_signal_received", signal=signum)
        shutdown.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Background cache cleanup thread
    cleanup_thread = threading.Thread(
        target=_cache_cleanup_loop,
        args=(cache, shutdown),
        daemon=True,
    )
    cleanup_thread.start()

    log.info("worker_started")

    # Main poll loop
    while not shutdown.is_set():
        try:
            tasks = queue.poll(max_messages=1)
        except Exception:
            log.exception("poll_error")
            # Back off on poll errors to avoid tight error loops
            time.sleep(5)
            continue

        for task in tasks:
            try:
                log.info(
                    "processing_task",
                    delivery_id=task.delivery_id,
                    url=task.url,
                )
                process_task(
                    task,
                    settings=settings,
                    conn=conn,
                    email_sender=email_sender,
                    cache=cache,
                )
                log.info("task_completed", delivery_id=task.delivery_id)
            except Exception:
                # CRITICAL: Always ACK — never let a message become a poison pill.
                # The DLQ (maxReceiveCount=3) handles true retries.
                log.exception(
                    "task_failed",
                    delivery_id=task.delivery_id,
                )
                try:
                    update_delivery_status(
                        conn,
                        task.delivery_id,
                        "Failed",
                        error_message="Unexpected worker error",
                    )
                except Exception:
                    log.exception(
                        "status_update_failed",
                        delivery_id=task.delivery_id,
                    )
            finally:
                # Always ACK the message regardless of outcome
                try:
                    queue.ack(task.receipt_handle)
                except Exception:
                    log.exception(
                        "ack_failed",
                        delivery_id=task.delivery_id,
                    )

    # Shutdown
    log.info("shutting_down")
    try:
        conn.close()
        log.info("db_connection_closed")
    except Exception:
        log.exception("db_close_error")
    log.info("worker_stopped")


if __name__ == "__main__":
    main()
