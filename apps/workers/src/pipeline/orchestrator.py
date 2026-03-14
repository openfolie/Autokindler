"""Full pipeline: resolve → cache check → download → convert → size guard → email → status update."""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import structlog

from ..cache.file_cache import FileCache
from ..config import Settings
from ..db import update_delivery_status
from ..email.interface import EmailSender
from ..queue.interface import DeliveryTask
from .converter import ConversionError, ConversionTimeoutError, convert_html_to_epub
from .downloader import (
    ContentValidationError,
    DownloadTimeoutError,
    FileTooLargeError,
    UnsupportedContentTypeError,
    download,
)
from .resolver import resolve_urls
from .size_guard import check_encoded_size, check_size

log = structlog.get_logger()


class JobTimeoutError(Exception):
    """Overall job exceeded the allowed timeout."""


def process_delivery(
    task: DeliveryTask,
    cache: FileCache,
    email_sender: EmailSender,
    db_conn,
    settings: Settings,
) -> None:
    """Execute the full delivery pipeline for a single task.

    Steps:
        1. Resolve URLs (arXiv detection, html/pdf derivation)
        2. Check cache
        3. Try HTML → EPUB conversion (if html_url available)
        4. PDF fallback (if HTML failed or unavailable)
        5. Size guard (raw + encoded)
        6. Email to Kindle
        7. Update delivery status

    This function NEVER raises. All errors are caught, logged, and persisted
    to the delivery_log table with a descriptive error_message.
    """
    start = time.monotonic()
    delivery_id = task.delivery_id

    # Job-level timeout using a threading.Timer
    timed_out = threading.Event()

    def _job_timeout():
        timed_out.set()

    timer = threading.Timer(settings.JOB_TIMEOUT, _job_timeout)
    timer.start()

    try:
        _run_pipeline(task, cache, email_sender, db_conn, settings, timed_out)
    except JobTimeoutError:
        duration = time.monotonic() - start
        log.error(
            "job_timeout",
            delivery_id=delivery_id,
            timeout=settings.JOB_TIMEOUT,
            duration_s=round(duration, 1),
        )
        _safe_update_status(
            db_conn,
            delivery_id,
            "Failed",
            f"Job timed out after {settings.JOB_TIMEOUT}s",
        )
    except FileTooLargeError as exc:
        log.warning(
            "file_too_large",
            delivery_id=delivery_id,
            error=str(exc),
        )
        _safe_update_status(db_conn, delivery_id, "Failed", str(exc))
    except Exception as exc:
        duration = time.monotonic() - start
        log.exception(
            "pipeline_error",
            delivery_id=delivery_id,
            duration_s=round(duration, 1),
        )
        _safe_update_status(
            db_conn,
            delivery_id,
            "Failed",
            f"Internal error: {str(exc)[:500]}",
        )
    finally:
        timer.cancel()
        duration = time.monotonic() - start
        log.info(
            "pipeline_finished",
            delivery_id=delivery_id,
            duration_s=round(duration, 1),
        )


def _run_pipeline(
    task: DeliveryTask,
    cache: FileCache,
    email_sender: EmailSender,
    db_conn,
    settings: Settings,
    timed_out: threading.Event,
) -> None:
    """Inner pipeline logic — may raise exceptions caught by process_delivery."""
    delivery_id = task.delivery_id

    def _check_timeout():
        if timed_out.is_set():
            raise JobTimeoutError(f"Job exceeded {settings.JOB_TIMEOUT}s timeout")

    # Step 1 — Resolve URLs
    log.info("pipeline_step", step="resolve", delivery_id=delivery_id, url=task.url)
    resolved = resolve_urls(task.url)
    log.info(
        "urls_resolved",
        delivery_id=delivery_id,
        html_url=resolved["html_url"],
        pdf_url=resolved["pdf_url"],
        format_hint=resolved["format_hint"],
    )
    _check_timeout()

    # Step 2 — Check cache
    # Try EPUB first, then PDF
    cached_path = cache.get(task.url, ext=".epub") or cache.get(task.url, ext=".pdf")
    if cached_path:
        log.info("cache_hit", delivery_id=delivery_id, path=cached_path)
        _email_and_complete(cached_path, task, email_sender, db_conn, settings)
        return

    log.info("cache_miss", delivery_id=delivery_id)

    # Step 3 — Try HTML first (if html_url available)
    final_path: str | None = None

    if resolved["html_url"]:
        try:
            log.info(
                "pipeline_step",
                step="download_html",
                delivery_id=delivery_id,
                url=resolved["html_url"],
            )
            html_file = download(
                resolved["html_url"],
                settings.CACHE_DIR,
                timeout=settings.DOWNLOAD_TIMEOUT,
            )
            _check_timeout()

            log.info(
                "pipeline_step",
                step="convert_html",
                delivery_id=delivery_id,
                html_path=html_file.path,
            )
            epub_path = convert_html_to_epub(
                html_file.path,
                settings.CACHE_DIR,
                timeout=settings.CONVERSION_TIMEOUT,
            )
            final_path = epub_path
            cache.put(task.url, epub_path, "application/epub+zip")
            log.info(
                "html_conversion_success",
                delivery_id=delivery_id,
                epub_path=epub_path,
            )
        except (
            ConversionError,
            ConversionTimeoutError,
            DownloadTimeoutError,
            UnsupportedContentTypeError,
            ContentValidationError,
            httpx.HTTPStatusError,
        ) as exc:
            log.warning(
                "html_conversion_failed",
                delivery_id=delivery_id,
                reason=str(exc),
            )
            # Fall through to PDF fallback
        except FileTooLargeError:
            # Size error is fatal — no point trying PDF fallback
            raise

    _check_timeout()

    # Step 4 — PDF fallback (if HTML failed or no html_url)
    if final_path is None and resolved["pdf_url"]:
        log.info(
            "pipeline_step",
            step="download_pdf_fallback",
            delivery_id=delivery_id,
            url=resolved["pdf_url"],
        )
        pdf_file = download(
            resolved["pdf_url"],
            settings.CACHE_DIR,
            timeout=settings.DOWNLOAD_TIMEOUT,
        )
        final_path = pdf_file.path
        cache.put(task.url, pdf_file.path, "application/pdf")
        log.info(
            "pdf_fallback_success",
            delivery_id=delivery_id,
            pdf_path=pdf_file.path,
        )

    if final_path is None:
        raise RuntimeError(
            f"No download URL available for {task.url} "
            f"(html={resolved['html_url']}, pdf={resolved['pdf_url']})"
        )

    _check_timeout()

    # Step 5 — Size guard
    log.info("pipeline_step", step="size_guard", delivery_id=delivery_id)
    check_size(final_path)
    check_encoded_size(final_path)

    _check_timeout()

    # Step 6+7 — Email and update status
    _email_and_complete(final_path, task, email_sender, db_conn, settings)


def _email_and_complete(
    file_path: str,
    task: DeliveryTask,
    email_sender: EmailSender,
    db_conn,
    settings: Settings,
) -> None:
    """Send email with attachment and update status to Completed."""
    delivery_id = task.delivery_id
    filename = _derive_filename(task.url, file_path)

    log.info(
        "pipeline_step",
        step="email",
        delivery_id=delivery_id,
        filename=filename,
    )

    email_sender.send(
        to_email=task.kindle_email,
        subject=f"AutoKindler: {filename}",
        body="Your paper is attached.",
        attachment_path=file_path,
        attachment_filename=filename,
    )

    update_delivery_status(db_conn, delivery_id, "Completed")
    log.info("delivery_completed", delivery_id=delivery_id, filename=filename)


def _derive_filename(url: str, file_path: str) -> str:
    """Derive a human-readable filename from the URL and file extension.

    For arXiv: ``2301.12345.epub`` or ``2301.12345.pdf``
    For others: last path segment + correct extension.
    """
    ext = Path(file_path).suffix  # .epub or .pdf

    # Try to extract arXiv paper ID
    arxiv_new = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if arxiv_new:
        return f"{arxiv_new.group(1)}{ext}"

    arxiv_old = re.search(r"([a-z-]+/\d{7}(?:v\d+)?)", url)
    if arxiv_old:
        # Replace / with - for filename safety
        return f"{arxiv_old.group(1).replace('/', '-')}{ext}"

    # Fallback: use last path segment
    parsed = urlparse(url)
    last_segment = parsed.path.rstrip("/").split("/")[-1]
    if last_segment:
        # Strip existing extension, add correct one
        base = Path(last_segment).stem
        return f"{base}{ext}"

    return f"document{ext}"


def _safe_update_status(
    db_conn,
    delivery_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update delivery status, catching any DB errors."""
    try:
        update_delivery_status(db_conn, delivery_id, status, error_message)
    except Exception:
        log.exception(
            "status_update_failed",
            delivery_id=delivery_id,
            status=status,
        )
