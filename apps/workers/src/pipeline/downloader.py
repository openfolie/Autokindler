"""Streaming HTTP download with Content-Length pre-check, byte counter cutoff, and content-type validation."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog

log = structlog.get_logger()

# User-Agent for polite crawling
USER_AGENT = "AutoKindler/1.0 (https://github.com/openfolie/autokindler)"

# Allowed Content-Types
_ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/html": ".html",
}

# Magic bytes for content validation
_PDF_MAGIC = b"%PDF"
_HTML_STARTS = (b"<", b"<!")


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------


class FileTooLargeError(Exception):
    """File exceeds the allowed size limit."""


class UnsupportedContentTypeError(Exception):
    """Downloaded file has an unsupported Content-Type."""


class ContentValidationError(Exception):
    """File content does not match its declared Content-Type (magic bytes mismatch)."""


class DownloadTimeoutError(Exception):
    """Download timed out."""


# ------------------------------------------------------------------
# Download result
# ------------------------------------------------------------------


@dataclass
class DownloadResult:
    """Result of a successful download."""

    path: str
    content_type: str
    size: int


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def download(
    url: str,
    dest_dir: str,
    timeout: int = 60,
    max_size: int = 9 * 1024 * 1024,
) -> DownloadResult:
    """Download a file from *url* into *dest_dir*.

    Steps:
        1. HEAD request — reject if Content-Length > max_size
        2. Streaming GET — validate Content-Type, stream with byte counter
        3. Magic bytes validation
        4. Atomic rename from .tmp to final filename

    Returns:
        DownloadResult with path, content_type, and size.

    Raises:
        FileTooLargeError: File exceeds max_size.
        UnsupportedContentTypeError: Content-Type not application/pdf or text/html.
        ContentValidationError: Magic bytes don't match Content-Type.
        DownloadTimeoutError: Download exceeded timeout.
        httpx.HTTPStatusError: Non-2xx HTTP response.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    http_timeout = httpx.Timeout(timeout, connect=15.0)

    # Step 1 — HEAD request: pre-check Content-Length
    try:
        head_resp = httpx.head(
            url,
            headers=headers,
            timeout=http_timeout,
            follow_redirects=True,
        )
        content_length = head_resp.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            raise FileTooLargeError(
                f"Content-Length {int(content_length)} exceeds limit of {max_size} bytes "
                f"({int(content_length) / (1024 * 1024):.1f} MB > {max_size / (1024 * 1024):.0f} MB)"
            )
    except httpx.TimeoutException as exc:
        raise DownloadTimeoutError(
            f"HEAD request timed out after {timeout}s: {url}"
        ) from exc

    # Step 2 — Streaming GET
    try:
        with httpx.stream(
            "GET",
            url,
            headers=headers,
            timeout=http_timeout,
            follow_redirects=True,
        ) as response:
            response.raise_for_status()

            # Validate Content-Type
            raw_ct = response.headers.get("content-type", "")
            content_type = _normalize_content_type(raw_ct)
            if content_type not in _ALLOWED_CONTENT_TYPES:
                raise UnsupportedContentTypeError(
                    f"Unsupported Content-Type: {raw_ct} (normalized: {content_type}). "
                    f"Allowed: {', '.join(_ALLOWED_CONTENT_TYPES)}"
                )

            ext = _ALLOWED_CONTENT_TYPES[content_type]
            file_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            tmp_path = dest / f"{file_hash}{ext}.tmp"
            final_path = dest / f"{file_hash}{ext}"

            # Step 3 — Stream to .tmp file with byte counter
            total_bytes = 0
            try:
                with tmp_path.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > max_size:
                            raise FileTooLargeError(
                                f"Download exceeded {max_size} bytes mid-stream "
                                f"({total_bytes / (1024 * 1024):.1f} MB > "
                                f"{max_size / (1024 * 1024):.0f} MB)"
                            )
                        f.write(chunk)
            except FileTooLargeError:
                tmp_path.unlink(missing_ok=True)
                raise

    except httpx.TimeoutException as exc:
        raise DownloadTimeoutError(
            f"Download timed out after {timeout}s: {url}"
        ) from exc

    # Step 4 — Magic bytes validation
    _validate_magic_bytes(tmp_path, content_type)

    # Step 5 — Atomic rename
    os.rename(str(tmp_path), str(final_path))

    log.info(
        "download_complete",
        url=url,
        path=str(final_path),
        content_type=content_type,
        size=total_bytes,
    )

    return DownloadResult(
        path=str(final_path),
        content_type=content_type,
        size=total_bytes,
    )


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _normalize_content_type(raw: str) -> str:
    """Strip parameters (charset etc.) from Content-Type header."""
    return raw.split(";")[0].strip().lower()


def _validate_magic_bytes(file_path: Path, content_type: str) -> None:
    """Check that the first bytes of the file match the declared Content-Type."""
    with file_path.open("rb") as f:
        head = f.read(16)

    if not head:
        raise ContentValidationError(f"Downloaded file is empty: {file_path}")

    if content_type == "application/pdf":
        if not head.startswith(_PDF_MAGIC):
            raise ContentValidationError(
                f"File declared as PDF but does not start with %PDF magic bytes. "
                f"First bytes: {head[:8]!r}"
            )
    elif content_type == "text/html":
        # HTML may have leading whitespace / BOM
        stripped = head.lstrip()
        if not any(stripped.startswith(m) for m in _HTML_STARTS):
            raise ContentValidationError(
                f"File declared as HTML but does not start with '<'. "
                f"First bytes: {head[:8]!r}"
            )
