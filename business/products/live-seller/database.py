"""
SQLite database initialization and schema for Live Seller app.
Uses WAL mode for better concurrent read/write performance.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DB_PATH, SECURE_DIR


DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    description TEXT,
    base_price  REAL    NOT NULL,
    image_url   TEXT,
    is_active   INTEGER DEFAULT 1,
    created_at  INTEGER DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS variants (
    id              INTEGER PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    label           TEXT    NOT NULL,
    price_modifier  REAL    DEFAULT 0.0,
    stock           INTEGER NOT NULL DEFAULT 0,
    sku             TEXT,
    UNIQUE(product_id, label)
);

CREATE TABLE IF NOT EXISTS buyers (
    id                  INTEGER PRIMARY KEY,
    platform            TEXT    NOT NULL,
    platform_user_id    TEXT    NOT NULL,
    display_name        TEXT,
    handle              TEXT,
    total_orders        INTEGER DEFAULT 0,
    total_spend         REAL    DEFAULT 0.0,
    is_vip              INTEGER DEFAULT 0,
    first_seen          INTEGER DEFAULT (unixepoch()),
    UNIQUE(platform, platform_user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY,
    platform        TEXT    NOT NULL DEFAULT 'manual',
    live_id         TEXT,
    title           TEXT,
    started_at      INTEGER DEFAULT (unixepoch()),
    ended_at        INTEGER,
    status          TEXT    DEFAULT 'active',
    total_orders    INTEGER DEFAULT 0,
    total_revenue   REAL    DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY,
    session_id          INTEGER NOT NULL REFERENCES sessions(id),
    buyer_id            INTEGER NOT NULL REFERENCES buyers(id),
    product_id          INTEGER NOT NULL REFERENCES products(id),
    variant_id          INTEGER REFERENCES variants(id),
    qty                 INTEGER NOT NULL DEFAULT 1,
    unit_price          REAL    NOT NULL,
    total_price         REAL    NOT NULL,
    status              TEXT    DEFAULT 'pending',
    raw_comment         TEXT    NOT NULL,
    platform_comment_id TEXT,
    confidence          REAL,
    extracted_at        INTEGER DEFAULT (unixepoch()),
    confirmed_at        INTEGER,
    printed_at          INTEGER,
    reply_posted        INTEGER DEFAULT 0,
    reply_text          TEXT
);

CREATE TABLE IF NOT EXISTS comment_log (
    id                  INTEGER PRIMARY KEY,
    session_id          INTEGER REFERENCES sessions(id),
    platform            TEXT    NOT NULL DEFAULT 'manual',
    platform_comment_id TEXT,
    raw_text            TEXT    NOT NULL,
    handle              TEXT,
    intent              TEXT,
    processed_at        INTEGER DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS bid_sessions (
    id                      INTEGER PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES sessions(id),
    product_id              INTEGER NOT NULL REFERENCES products(id),
    variant_id              INTEGER REFERENCES variants(id),
    title                   TEXT,
    starting_price          REAL    NOT NULL,
    min_increment           REAL    NOT NULL DEFAULT 10.0,
    countdown_seconds       INTEGER NOT NULL DEFAULT 60,
    status                  TEXT    DEFAULT 'active',
    current_highest_bid     REAL,
    current_winner_buyer_id INTEGER REFERENCES buyers(id),
    started_at              INTEGER DEFAULT (unixepoch()),
    ends_at                 INTEGER,
    closed_at               INTEGER,
    winner_order_id         INTEGER REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS bids (
    id                  INTEGER PRIMARY KEY,
    bid_session_id      INTEGER NOT NULL REFERENCES bid_sessions(id),
    buyer_id            INTEGER NOT NULL REFERENCES buyers(id),
    amount              REAL    NOT NULL,
    platform_comment_id TEXT,
    raw_comment         TEXT    NOT NULL,
    placed_at           INTEGER DEFAULT (unixepoch()),
    placed_at_ms        INTEGER,
    is_winning          INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_session    ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_buyer      ON orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_buyers_platform   ON buyers(platform, platform_user_id);
CREATE INDEX IF NOT EXISTS idx_comment_log_sess  ON comment_log(session_id);
CREATE INDEX IF NOT EXISTS idx_bid_sessions_sess ON bid_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_bids_bid_sess     ON bids(bid_session_id);
CREATE INDEX IF NOT EXISTS idx_bids_buyer        ON bids(buyer_id);
"""


def get_connection() -> sqlite3.Connection:
    SECURE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(DDL)
        conn.commit()
    finally:
        conn.close()
