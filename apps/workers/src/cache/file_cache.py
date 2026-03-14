"""Flat-directory file cache with metadata sidecars and TTL auto-cleanup."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

log = structlog.get_logger()


class FileCache:
    """Cache downloaded/converted files on disk with URL-hash keys.

    Each cached entry consists of two files:
    - ``<hash>.<ext>``  — the data file
    - ``<hash>.meta.json`` — metadata sidecar (url, cached_at, content_type, size_bytes)

    Atomic writes: data is first written to a ``.tmp`` suffix then renamed.
    Orphans (one file of a pair missing) are cleaned up automatically.
    """

    def __init__(self, cache_dir: str, ttl_days: int = 3) -> None:
        self._cache_dir = Path(cache_dir)
        self._ttl = timedelta(days=ttl_days)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, url: str, ext: str = ".epub") -> str | None:
        """Return the cached file path for *url*, or ``None`` on miss.

        Handles expiry and orphan cleanup transparently.
        """
        key = self._hash_url(url)
        data_path = self._cache_dir / f"{key}{ext}"
        meta_path = self._meta_path(data_path)

        data_exists = data_path.exists()
        meta_exists = meta_path.exists()

        # Orphan handling
        if data_exists != meta_exists:
            log.warning("cache_orphan", key=key, data=data_exists, meta=meta_exists)
            data_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            return None

        if not data_exists:
            return None

        # Expiry check
        try:
            meta = json.loads(meta_path.read_text())
            cached_at = datetime.fromisoformat(meta["cached_at"])
            if datetime.now(timezone.utc) - cached_at > self._ttl:
                log.info("cache_expired", key=key, url=url)
                data_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return None
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupt metadata — treat as miss
            data_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            return None

        log.debug("cache_hit", key=key, url=url)
        return str(data_path)

    def put(self, url: str, file_path: str, content_type: str) -> str:
        """Copy *file_path* into the cache and return the cached path.

        Preserves the source file's extension. Uses atomic rename.
        """
        src = Path(file_path)
        ext = src.suffix or ".bin"
        key = self._hash_url(url)
        dest = self._cache_dir / f"{key}{ext}"
        tmp = dest.with_suffix(dest.suffix + ".tmp")

        # Atomic write: copy to .tmp then rename
        shutil.copy2(str(src), str(tmp))
        os.rename(str(tmp), str(dest))

        # Write metadata sidecar
        meta = {
            "url": url,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "size_bytes": dest.stat().st_size,
        }
        meta_path = self._meta_path(dest)
        meta_path.write_text(json.dumps(meta, indent=2))

        log.info("cache_put", key=key, url=url, size=meta["size_bytes"])
        return str(dest)

    def cleanup(self) -> int:
        """Delete expired entries and orphans. Return count of deleted entries."""
        deleted = 0
        now = datetime.now(timezone.utc)
        seen_keys: dict[str, dict[str, Path]] = {}

        # Gather all files grouped by key (stem without extension)
        for path in self._cache_dir.iterdir():
            if not path.is_file():
                continue
            # Meta files end with .meta.json
            if path.name.endswith(".meta.json"):
                key = path.name.removesuffix(".meta.json")
                seen_keys.setdefault(key, {})["meta"] = path
            else:
                key = path.stem
                seen_keys.setdefault(key, {})["data"] = path

        for key, files in seen_keys.items():
            data_path = files.get("data")
            meta_path = files.get("meta")

            # Orphan: one file missing
            if data_path is None or meta_path is None:
                log.info("cleanup_orphan", key=key)
                if data_path:
                    data_path.unlink(missing_ok=True)
                if meta_path:
                    meta_path.unlink(missing_ok=True)
                deleted += 1
                continue

            # Check expiry
            try:
                meta = json.loads(meta_path.read_text())
                cached_at = datetime.fromisoformat(meta["cached_at"])
                if now - cached_at > self._ttl:
                    log.info("cleanup_expired", key=key, url=meta.get("url"))
                    data_path.unlink(missing_ok=True)
                    meta_path.unlink(missing_ok=True)
                    deleted += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                log.warning("cleanup_corrupt_meta", key=key)
                data_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                deleted += 1

        if deleted:
            log.info("cache_cleanup_complete", deleted=deleted)
        return deleted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_url(url: str) -> str:
        """SHA-256 hex digest of *url*, first 16 characters."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    @staticmethod
    def _meta_path(data_path: Path) -> Path:
        """Return the metadata sidecar path for a given data file."""
        return data_path.with_name(data_path.stem + ".meta.json")
