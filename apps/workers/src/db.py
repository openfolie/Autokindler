"""Postgres database client for delivery_log status updates."""

from __future__ import annotations

import psycopg
import structlog

log = structlog.get_logger()


def get_connection(database_url: str) -> psycopg.Connection:
    """Open a psycopg connection with autocommit enabled."""
    conn = psycopg.connect(database_url, autocommit=True)
    log.info("db_connected", url=database_url.split("@")[-1])  # log host only
    return conn


def update_delivery_status(
    conn: psycopg.Connection,
    delivery_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update the delivery_log row with a new status and optional error."""
    conn.execute(
        "UPDATE delivery_log SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s",
        (status, error_message, delivery_id),
    )
    log.info("delivery_status_updated", delivery_id=delivery_id, status=status)


def get_kindle_email(
    conn: psycopg.Connection,
    delivery_id: str,
) -> str | None:
    """Look up the Kindle email for a delivery via its user."""
    row = conn.execute(
        "SELECT u.kindle_email FROM users u JOIN delivery_log d ON d.user_id = u.id WHERE d.id = %s",
        (delivery_id,),
    ).fetchone()
    return row[0] if row else None
