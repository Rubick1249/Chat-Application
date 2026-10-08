"""
database.py - SQLite setup for ShieldChat.

Creates the tables on first run and seeds three demo users.
All queries in this project use "?" placeholders (parameterised queries),
never string formatting, so user input can never change the SQL itself.
This is the standard defence against SQL injection.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shieldchat.db")

# Demo users (fake accounts for the college demo only).
SEED_USERS = [
    ("alice@shieldcorp.com", "Alice", "Alice@123", "employee"),
    ("bob@shieldcorp.com", "Bob", "Bob@123", "employee"),
    ("admin@shieldcorp.com", "Security Admin", "Admin@123", "admin"),
]


def get_db():
    """Open a new connection to the SQLite file; rows behave like dicts."""
    # check_same_thread=False because Flask-SocketIO (threading mode) may use
    # the connection from a different thread than the one that opened it.
    # We open a fresh connection per request/event, so this is safe.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables (if missing) and add the demo users on first run."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            password_hash   TEXT NOT NULL,      -- never the plain password
            role            TEXT NOT NULL DEFAULT 'employee',
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until    TEXT                -- ISO time, NULL = not locked
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text        TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        );

        -- Security incidents for the admin dashboard.
        -- 'details' only ever holds MASKED values (see dlp.py), never raw data.
        CREATE TABLE IF NOT EXISTS dlp_incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email  TEXT NOT NULL,
            type        TEXT NOT NULL,
            details     TEXT,
            created_at  TEXT NOT NULL
        );
        """
    )

    for email, name, password, role in SEED_USERS:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if not exists:
            # Hash the password before storing it. A hash is one-way, so even
            # if the database file is stolen the real passwords are not exposed.
            conn.execute(
                "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                (email, name, generate_password_hash(password), role),
            )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database ready at", DB_PATH)
