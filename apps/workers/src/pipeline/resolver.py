"""URL format detection and arXiv URL resolution (abs → html/pdf)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import structlog

log = structlog.get_logger()

# Matches arXiv paper IDs:
#   - New format: 2301.12345, 2301.12345v2
#   - Old format: hep-th/9901001, hep-th/9901001v2
_ARXIV_NEW_ID = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")
_ARXIV_OLD_ID = re.compile(r"([a-z-]+/\d{7}(?:v\d+)?)")


def resolve_urls(url: str) -> dict:
    """Resolve a URL into html_url, pdf_url, and format_hint.

    Returns::

        {
            "html_url": str | None,
            "pdf_url": str | None,
            "format_hint": "html" | "pdf" | "unknown",
        }

    For arXiv URLs, derives both HTML and PDF download links from the paper ID.
    For non-arXiv URLs, returns the URL as-is with format detection from extension.

    Raises:
        ValueError: If the URL is not HTTPS or is malformed.
    """
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Malformed URL: {url}")
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are supported, got {parsed.scheme}: {url}")

    # Check if arXiv
    if "arxiv.org" in parsed.netloc:
        return _resolve_arxiv(url, parsed.path)

    # Non-arXiv: detect format from extension
    return _resolve_generic(url, parsed.path)


def _resolve_arxiv(url: str, path: str) -> dict:
    """Resolve an arXiv URL to html/pdf download links."""
    paper_id = _extract_arxiv_id(path)
    if paper_id is None:
        log.warning("arxiv_id_not_found", url=url)
        return _resolve_generic(url, path)

    html_url = f"https://arxiv.org/html/{paper_id}"
    pdf_url = f"https://arxiv.org/pdf/{paper_id}"

    # Determine format hint from the original URL path
    if "/html/" in path:
        format_hint = "html"
    elif "/pdf/" in path:
        format_hint = "pdf"
    else:
        # abs or other — default to html (we prefer EPUB conversion)
        format_hint = "html"

    log.info(
        "arxiv_resolved",
        paper_id=paper_id,
        html_url=html_url,
        pdf_url=pdf_url,
        format_hint=format_hint,
    )

    return {
        "html_url": html_url,
        "pdf_url": pdf_url,
        "format_hint": format_hint,
    }


def _extract_arxiv_id(path: str) -> str | None:
    """Extract the paper ID from an arXiv URL path."""
    # Try new-format IDs first (e.g., 2301.12345, 2301.12345v2)
    m = _ARXIV_NEW_ID.search(path)
    if m:
        return m.group(1)

    # Try old-format IDs (e.g., hep-th/9901001)
    m = _ARXIV_OLD_ID.search(path)
    if m:
        return m.group(1)

    return None


def _resolve_generic(url: str, path: str) -> dict:
    """Resolve a non-arXiv URL based on file extension."""
    lower_path = path.lower()

    if lower_path.endswith(".pdf"):
        format_hint = "pdf"
    elif lower_path.endswith((".html", ".htm")):
        format_hint = "html"
    else:
        format_hint = "unknown"

    result = {
        "html_url": url if format_hint in ("html", "unknown") else None,
        "pdf_url": url if format_hint in ("pdf", "unknown") else None,
        "format_hint": format_hint,
    }

    log.info("url_resolved", url=url, format_hint=format_hint)
    return result
