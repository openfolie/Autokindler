"""HTML-to-EPUB conversion via pypandoc with timeout."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

import structlog

log = structlog.get_logger()


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------


class ConversionError(Exception):
    """HTML-to-EPUB conversion failed."""


class ConversionTimeoutError(ConversionError):
    """Pandoc process exceeded the allowed timeout."""


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def convert_html_to_epub(
    html_path: str,
    output_dir: str,
    timeout: int = 120,
) -> str:
    """Convert an HTML file to EPUB using pandoc.

    Uses subprocess directly (instead of pypandoc's Python API) to enable
    reliable process-level timeout via ``subprocess.Popen.kill()``.

    Args:
        html_path: Path to the source HTML file.
        output_dir: Directory for the output EPUB file.
        timeout: Maximum seconds for the conversion. Defaults to 120.

    Returns:
        Path to the generated EPUB file.

    Raises:
        ConversionTimeoutError: Pandoc exceeded *timeout*.
        ConversionError: Pandoc exited with a non-zero code.
        FileNotFoundError: *html_path* does not exist.
    """
    src = Path(html_path)
    if not src.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{src.stem}.epub"
    resource_path = str(src.parent)

    start = time.monotonic()

    # Build pandoc command
    cmd = [
        "pandoc",
        str(src),
        "-o",
        str(output_path),
        "--resource-path",
        resource_path,
    ]

    log.info(
        "conversion_starting",
        html_path=html_path,
        output_path=str(output_path),
        timeout=timeout,
    )

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Use a timer to kill the process if it exceeds timeout
    timed_out = threading.Event()

    def _kill():
        timed_out.set()
        proc.kill()

    timer = threading.Timer(timeout, _kill)
    timer.start()

    try:
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()

    duration = time.monotonic() - start

    if timed_out.is_set():
        log.error(
            "conversion_timeout",
            html_path=html_path,
            timeout=timeout,
            duration_s=round(duration, 1),
        )
        # Clean up partial output
        output_path.unlink(missing_ok=True)
        raise ConversionTimeoutError(
            f"Pandoc conversion timed out after {timeout}s for {html_path}"
        )

    if proc.returncode != 0:
        stderr_text = stderr.decode(errors="replace").strip()
        log.error(
            "conversion_failed",
            html_path=html_path,
            exit_code=proc.returncode,
            stderr=stderr_text[:500],
            duration_s=round(duration, 1),
        )
        # Clean up partial output
        output_path.unlink(missing_ok=True)
        raise ConversionError(
            f"Pandoc failed (exit {proc.returncode}): {stderr_text[:300]}"
        )

    if not output_path.exists():
        raise ConversionError(f"Pandoc produced no output file at {output_path}")

    log.info(
        "conversion_complete",
        html_path=html_path,
        output_path=str(output_path),
        size_bytes=output_path.stat().st_size,
        duration_s=round(duration, 1),
    )

    return str(output_path)
