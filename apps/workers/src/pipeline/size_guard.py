"""Post-conversion size validation accounting for Base64 MIME inflation."""

from __future__ import annotations

import os

import structlog

from .downloader import FileTooLargeError

log = structlog.get_logger()

# Base64 encoding inflates by ~4/3 (1.333...) plus MIME header overhead.
# We use 1.37 as a conservative estimate.
BASE64_INFLATION_FACTOR = 1.37

# SES SMTP message size limit (raw MIME message)
SES_SMTP_MAX_SIZE = 40 * 1024 * 1024  # 40 MB


def check_size(
    file_path: str,
    max_raw_size: int = 9 * 1024 * 1024,
) -> None:
    """Validate that a file does not exceed the raw size limit.

    This is the user-facing size limit (9 MB by default). Applied before
    email send to give a clear error message.

    Raises:
        FileTooLargeError: File exceeds *max_raw_size*.
        FileNotFoundError: *file_path* does not exist.
    """
    size = os.path.getsize(file_path)

    if size > max_raw_size:
        log.warning(
            "size_check_failed",
            file_path=file_path,
            size_bytes=size,
            max_bytes=max_raw_size,
            size_mb=round(size / (1024 * 1024), 2),
            max_mb=round(max_raw_size / (1024 * 1024), 0),
        )
        raise FileTooLargeError(
            f"File exceeds {max_raw_size / (1024 * 1024):.0f} MB size limit "
            f"(actual: {size / (1024 * 1024):.1f} MB): {file_path}"
        )

    log.debug(
        "size_check_passed",
        file_path=file_path,
        size_bytes=size,
        max_bytes=max_raw_size,
    )


def check_encoded_size(
    file_path: str,
    max_encoded_size: int = SES_SMTP_MAX_SIZE,
) -> None:
    """Validate that a file's Base64-encoded size won't exceed the SES SMTP limit.

    Accounts for Base64 inflation (×1.37) plus MIME overhead. The SES SMTP
    interface limits raw MIME messages to 40 MB.

    Raises:
        FileTooLargeError: Estimated encoded size exceeds *max_encoded_size*.
        FileNotFoundError: *file_path* does not exist.
    """
    raw_size = os.path.getsize(file_path)
    estimated_encoded = int(raw_size * BASE64_INFLATION_FACTOR)

    if estimated_encoded > max_encoded_size:
        log.warning(
            "encoded_size_check_failed",
            file_path=file_path,
            raw_bytes=raw_size,
            estimated_encoded_bytes=estimated_encoded,
            max_encoded_bytes=max_encoded_size,
            raw_mb=round(raw_size / (1024 * 1024), 2),
            estimated_mb=round(estimated_encoded / (1024 * 1024), 2),
            max_mb=round(max_encoded_size / (1024 * 1024), 0),
        )
        raise FileTooLargeError(
            f"Estimated encoded size ({estimated_encoded / (1024 * 1024):.1f} MB) "
            f"exceeds SES {max_encoded_size / (1024 * 1024):.0f} MB SMTP limit "
            f"(raw: {raw_size / (1024 * 1024):.1f} MB × {BASE64_INFLATION_FACTOR} inflation): "
            f"{file_path}"
        )

    log.debug(
        "encoded_size_check_passed",
        file_path=file_path,
        raw_bytes=raw_size,
        estimated_encoded_bytes=estimated_encoded,
        max_encoded_bytes=max_encoded_size,
    )
