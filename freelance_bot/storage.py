from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from .models import Opportunity


SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    published_at TEXT NOT NULL,
    budget TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    reliability INTEGER NOT NULL DEFAULT 50,
    score INTEGER NOT NULL,
    reasons TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(database_path: str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(SCHEMA)
    ensure_column(connection, "source_url", "TEXT NOT NULL DEFAULT ''")
    ensure_column(connection, "reliability", "INTEGER NOT NULL DEFAULT 50")
    return connection


def save_new(connection: sqlite3.Connection, opportunities: list[Opportunity]) -> list[Opportunity]:
    new_items = []
    for item in opportunities:
        item_id = stable_id(item.url)
        try:
            connection.execute(
                """
                INSERT INTO opportunities
                (id, source, title, url, description, published_at, budget, source_url, reliability, score, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item.source,
                    item.title,
                    item.url,
                    item.description,
                    item.published_at,
                    item.budget,
                    item.source_url,
                    item.reliability,
                    item.score,
                    "; ".join(item.reasons),
                ),
            )
            new_items.append(item)
        except sqlite3.IntegrityError:
            continue
    connection.commit()
    return new_items


def stable_id(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()


def ensure_column(connection: sqlite3.Connection, name: str, definition: str) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(opportunities)")}
    if name not in columns:
        connection.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {definition}")
