import sqlite3
from config import settings, BASE_DIR

DB_PATH = BASE_DIR / settings.db_path


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS buyers (
                id              INTEGER PRIMARY KEY,
                tiktok_uid      TEXT    NOT NULL UNIQUE,
                display_name    TEXT    NOT NULL,
                handle          TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'new',
                total_mines     INTEGER DEFAULT 0,
                first_seen      INTEGER DEFAULT (unixepoch()),
                last_seen       INTEGER DEFAULT (unixepoch())
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY,
                tiktok_user     TEXT    NOT NULL,
                started_at      INTEGER DEFAULT (unixepoch()),
                ended_at        INTEGER,
                status          TEXT    DEFAULT 'active',
                total_mines     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS mines (
                id                  INTEGER PRIMARY KEY,
                session_id          INTEGER NOT NULL REFERENCES sessions(id),
                buyer_id            INTEGER NOT NULL REFERENCES buyers(id),
                price               REAL    NOT NULL,
                mined_at            INTEGER DEFAULT (unixepoch()),
                printed             INTEGER DEFAULT 0,
                session_mine_count  INTEGER NOT NULL DEFAULT 1,
                raw_comment         TEXT    DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_mines_session ON mines(session_id);
            CREATE INDEX IF NOT EXISTS idx_mines_buyer   ON mines(buyer_id);
        """)
