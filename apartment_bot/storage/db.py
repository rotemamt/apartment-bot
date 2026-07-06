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

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id TEXT NOT NULL UNIQUE,
    telegram_username TEXT,
    status TEXT NOT NULL DEFAULT 'onboarding'
        CHECK(status IN ('onboarding', 'pending_approval', 'approved', 'blocked')),
    is_admin INTEGER NOT NULL DEFAULT 0,
    paused INTEGER NOT NULL DEFAULT 0,
    onboarding_step TEXT,
    filters TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_listings (
    user_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    matched INTEGER NOT NULL DEFAULT 0,
    matched_features TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','seen','interested','rejected')),
    alert_sent INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (user_id, listing_id)
);
CREATE INDEX IF NOT EXISTS idx_user_listings_user ON user_listings(user_id);
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
    # NOT WAL: WAL mode needs a shared -wal/-shm file kept in sync between
    # every process touching the db, but docker-compose bind-mounts only the
    # single listings.db file (not its directory) into each service - each
    # container ends up with its own private, uncoordinated -wal/-shm pair,
    # so containers silently stop seeing each other's writes. The default
    # rollback journal only needs the one shared file, which the bind mount
    # already provides consistently across containers.
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.executescript(SCHEMA)
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


# --- users -------------------------------------------------------------

def create_user(
    conn: sqlite3.Connection,
    telegram_chat_id: str,
    telegram_username: str | None = None,
    status: str = "onboarding",
    is_admin: bool = False,
    onboarding_step: str | None = None,
    filters: dict | None = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO users (telegram_chat_id, telegram_username, status, is_admin,
               onboarding_step, filters, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(telegram_chat_id), telegram_username, status, int(is_admin),
         onboarding_step, json.dumps(filters or {}), now, now),
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_chat_id(conn: sqlite3.Connection, telegram_chat_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM users WHERE telegram_chat_id = ?", (str(telegram_chat_id),)
    ).fetchone()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_any_user(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users LIMIT 1").fetchone()


def get_active_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Users who should receive alerts on this scan cycle."""
    return conn.execute(
        "SELECT * FROM users WHERE status = 'approved' AND paused = 0"
    ).fetchall()


def get_admins(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE is_admin = 1").fetchall()


def set_user_status(conn: sqlite3.Connection, user_id: int, status: str) -> None:
    if status not in ("onboarding", "pending_approval", "approved", "blocked"):
        raise ValueError(f"invalid status: {status}")
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE users SET status=?, updated_at=? WHERE id=?", (status, now, user_id))
    conn.commit()


def set_user_paused(conn: sqlite3.Connection, user_id: int, paused: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET paused=?, updated_at=? WHERE id=?", (int(paused), now, user_id)
    )
    conn.commit()


def get_user_filters(conn: sqlite3.Connection, user_id: int) -> dict:
    row = conn.execute("SELECT filters FROM users WHERE id = ?", (user_id,)).fetchone()
    return json.loads(row["filters"]) if row and row["filters"] else {}


def update_user_filters(conn: sqlite3.Connection, user_id: int, updates: dict) -> None:
    from apartment_bot.telegram.config_editor import EDITABLE_FILTER_KEYS

    unknown = set(updates) - EDITABLE_FILTER_KEYS
    if unknown:
        raise ValueError(f"not editable: {unknown}")

    current = get_user_filters(conn, user_id)
    for key, value in updates.items():
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        current[key] = value

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET filters=?, updated_at=? WHERE id=?",
        (json.dumps(current), now, user_id),
    )
    conn.commit()


def submit_onboarding(conn: sqlite3.Connection, user_id: int, updates: dict) -> None:
    """Merge the Mini App wizard's answers into a user's filters and mark
    them ready for admin review. Reuses update_user_filters' key validation."""
    if updates:
        update_user_filters(conn, user_id, updates)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET status='pending_approval', updated_at=? WHERE id=?",
        (now, user_id),
    )
    conn.commit()


# --- user_listings -------------------------------------------------------

def upsert_user_listing(
    conn: sqlite3.Connection, user_id: int, listing_id: int, matched: bool, matched_features: list[str] | None
) -> bool:
    """Record how a listing evaluates for a specific user. Returns True if this
    is the first time this user has seen this listing."""
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        "SELECT 1 FROM user_listings WHERE user_id = ? AND listing_id = ?", (user_id, listing_id)
    ).fetchone()

    if row:
        conn.execute(
            """UPDATE user_listings SET matched=?, matched_features=?, last_seen_at=?
               WHERE user_id=? AND listing_id=?""",
            (int(matched), json.dumps(matched_features or []), now, user_id, listing_id),
        )
        conn.commit()
        return False

    conn.execute(
        """INSERT INTO user_listings
           (user_id, listing_id, matched, matched_features, status, alert_sent, first_seen_at, last_seen_at)
           VALUES (?, ?, ?, ?, 'new', 0, ?, ?)""",
        (user_id, listing_id, int(matched), json.dumps(matched_features or []), now, now),
    )
    conn.commit()
    return True


def get_user_listing_alert_sent(conn: sqlite3.Connection, user_id: int, listing_id: int) -> bool:
    row = conn.execute(
        "SELECT alert_sent FROM user_listings WHERE user_id = ? AND listing_id = ?",
        (user_id, listing_id),
    ).fetchone()
    return bool(row and row["alert_sent"])


def mark_alert_sent(conn: sqlite3.Connection, user_id: int, listing_id: int) -> None:
    conn.execute(
        "UPDATE user_listings SET alert_sent=1 WHERE user_id=? AND listing_id=?",
        (user_id, listing_id),
    )
    conn.commit()


def set_user_listing_status(conn: sqlite3.Connection, user_id: int, listing_id: int, status: str) -> None:
    if status not in ("new", "seen", "interested", "rejected"):
        raise ValueError(f"invalid status: {status}")
    conn.execute(
        "UPDATE user_listings SET status=? WHERE user_id=? AND listing_id=?",
        (status, user_id, listing_id),
    )
    conn.commit()


def count_user_matched_today(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        """SELECT COUNT(*) AS c FROM user_listings
           WHERE user_id = ? AND matched = 1 AND date(first_seen_at) = date('now')""",
        (user_id,),
    ).fetchone()
    return row["c"]


# sqlite3.Row resolves a duplicate column name (e.g. `status`) to the FIRST
# matching column, not the last - so `l.*, ul.status AS status` would silently
# keep the global listing's own status/matched columns and mask the per-user
# ones. List the listing columns explicitly, excluding the ones user_listings
# overrides, so there's no name collision at all.
_LISTING_COLUMNS_SQL = (
    "l.id, l.source, l.external_id, l.url, l.price, l.rooms, l.floor, l.sqm, "
    "l.address, l.photo_url, l.posted_date, l.raw_text, l.latitude, l.longitude"
)
_USER_LISTING_COLUMNS_SQL = (
    "ul.status AS status, ul.matched AS matched, ul.matched_features AS matched_features, "
    "ul.first_seen_at AS first_seen_at, ul.last_seen_at AS last_seen_at"
)


def get_user_listing(conn: sqlite3.Connection, user_id: int, listing_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"""SELECT {_LISTING_COLUMNS_SQL}, {_USER_LISTING_COLUMNS_SQL}
           FROM user_listings ul JOIN listings l ON l.id = ul.listing_id
           WHERE ul.user_id = ? AND ul.listing_id = ?""",
        (user_id, listing_id),
    ).fetchone()


def get_user_listings(
    conn: sqlite3.Connection,
    user_id: int,
    status: str | None = None,
    source: str | None = None,
    matched_only: bool = False,
    sort_by: str = "first_seen_at",
    order: str = "desc",
) -> list[sqlite3.Row]:
    if sort_by not in SORT_COLUMNS:
        raise ValueError(f"invalid sort_by: {sort_by}")
    order = "DESC" if order.lower() != "asc" else "ASC"
    sort_col = f"ul.{sort_by}" if sort_by == "first_seen_at" else f"l.{sort_by}"

    clauses = ["ul.user_id = ?"]
    params: list = [user_id]
    if status:
        clauses.append("ul.status = ?")
        params.append(status)
    if source:
        clauses.append("l.source = ?")
        params.append(source)
    if matched_only:
        clauses.append("ul.matched = 1")

    where = f"WHERE {' AND '.join(clauses)}"
    query = f"""
        SELECT {_LISTING_COLUMNS_SQL}, {_USER_LISTING_COLUMNS_SQL}
        FROM user_listings ul JOIN listings l ON l.id = ul.listing_id
        {where} ORDER BY {sort_col} {order}
    """
    return conn.execute(query, params).fetchall()
