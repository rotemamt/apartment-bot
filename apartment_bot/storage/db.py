import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apartment_bot.adapters.base import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT,
    url TEXT NOT NULL UNIQUE,
    price INTEGER,
    rooms REAL,
    floor INTEGER,
    sqm INTEGER,
    address TEXT,
    photo_url TEXT,
    posted_date TEXT,
    raw_text TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','seen','interested','rejected')),
    matched_features TEXT,
    matched INTEGER NOT NULL DEFAULT 0,
    latitude REAL,
    longitude REAL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
"""

# (column, definition) pairs added after the initial release - kept as idempotent
# ALTER TABLEs so existing databases upgrade in place without losing data.
MIGRATIONS = [
    ("matched", "INTEGER NOT NULL DEFAULT 0"),
    ("latitude", "REAL"),
    ("longitude", "REAL"),
]

SORT_COLUMNS = {"price", "rooms", "first_seen_at", "posted_date"}


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(SCHEMA)
    for column, definition in MIGRATIONS:
        try:
            conn.execute(f"ALTER TABLE listings ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def upsert_listing(
    conn: sqlite3.Connection, listing: Listing, matched_features: list[str] | None = None, matched: bool = False
) -> bool:
    """Insert a new listing or refresh an existing one. Returns True if this listing is new."""
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("SELECT id FROM listings WHERE url = ?", (listing.url,)).fetchone()

    if row:
        conn.execute(
            """UPDATE listings SET price=?, rooms=?, floor=?, sqm=?, address=?, photo_url=?,
               posted_date=?, raw_text=?, matched_features=?, matched=?, latitude=?, longitude=?,
               last_seen_at=? WHERE url=?""",
            (listing.price, listing.rooms, listing.floor, listing.sqm, listing.address,
             listing.photo_url, listing.posted_date, listing.raw_text,
             json.dumps(matched_features or []), int(matched), listing.latitude, listing.longitude,
             now, listing.url),
        )
        conn.commit()
        return False

    conn.execute(
        """INSERT INTO listings
           (source, external_id, url, price, rooms, floor, sqm, address, photo_url,
            posted_date, raw_text, status, matched_features, matched, latitude, longitude,
            first_seen_at, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?)""",
        (listing.source, listing.external_id, listing.url, listing.price, listing.rooms,
         listing.floor, listing.sqm, listing.address, listing.photo_url, listing.posted_date,
         listing.raw_text, json.dumps(matched_features or []), int(matched),
         listing.latitude, listing.longitude, now, now),
    )
    conn.commit()
    return True


def count_matched_today(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM listings WHERE matched=1 AND date(first_seen_at) = date('now')"
    ).fetchone()
    return row["c"]


def set_status(conn: sqlite3.Connection, listing_id: int, status: str) -> None:
    if status not in ("new", "seen", "interested", "rejected"):
        raise ValueError(f"invalid status: {status}")
    conn.execute("UPDATE listings SET status=? WHERE id=?", (status, listing_id))
    conn.commit()


def get_listings(
    conn: sqlite3.Connection,
    status: str | None = None,
    source: str | None = None,
    matched_only: bool = False,
    sort_by: str = "first_seen_at",
    order: str = "desc",
) -> list[sqlite3.Row]:
    if sort_by not in SORT_COLUMNS:
        raise ValueError(f"invalid sort_by: {sort_by}")
    order = "DESC" if order.lower() != "asc" else "ASC"

    clauses = []
    params: list = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if matched_only:
        clauses.append("matched = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM listings {where} ORDER BY {sort_by} {order}"
    return conn.execute(query, params).fetchall()


def get_listing(conn: sqlite3.Connection, listing_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
