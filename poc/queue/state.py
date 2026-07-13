"""SQLite-backed application state used independently from the queue broker."""

from __future__ import annotations

import os
import sqlite3
import time


DATABASE_PATH = os.environ.get("POC_DATABASE_PATH", "state.db")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                duration_seconds REAL NOT NULL,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                started_at REAL,
                finished_at REAL
            )
            """
        )


def reset_job(job_id: str, duration_seconds: float, *, cancelled: bool = False) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        connection.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, 'queued', 0, NULL, NULL)",
            (job_id, duration_seconds, int(cancelled)),
        )


def request_cancel(job_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE jobs SET cancel_requested = 1 WHERE id = ?", (job_id,)
        )


def snapshot(job_id: str) -> dict[str, object]:
    with connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise KeyError(job_id)
    return dict(row)


def execute_job(job_id: str) -> str:
    """Process one opaque ID and cooperate with durable cancellation intent."""
    with connect() as connection:
        job = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            raise KeyError(job_id)
        if job["cancel_requested"]:
            connection.execute(
                "UPDATE jobs SET state = 'cancelled', finished_at = ? WHERE id = ?",
                (time.monotonic(), job_id),
            )
            return "cancelled-before-start"
        connection.execute(
            "UPDATE jobs SET state = 'running', attempts = attempts + 1, started_at = ? WHERE id = ?",
            (time.monotonic(), job_id),
        )
        duration = float(job["duration_seconds"])

    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        time.sleep(0.05)
        with connect() as connection:
            cancelled = connection.execute(
                "SELECT cancel_requested FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()[0]
            if cancelled:
                connection.execute(
                    "UPDATE jobs SET state = 'cancelled', finished_at = ? WHERE id = ?",
                    (time.monotonic(), job_id),
                )
                return "cancelled-running"

    with connect() as connection:
        connection.execute(
            "UPDATE jobs SET state = 'completed', finished_at = ? WHERE id = ?",
            (time.monotonic(), job_id),
        )
    return "completed"
