import sqlite3
from pathlib import Path
from datetime import datetime

DEFAULT_DB = Path("data") / "data.db"

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT,
        role TEXT NOT NULL DEFAULT 'giocatore',
        force_password_change INTEGER DEFAULT 0,
        created_at DATETIME,
        updated_at DATETIME
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_number INTEGER UNIQUE NOT NULL,
        date TEXT UNIQUE NOT NULL,
        opponents_team TEXT NOT NULL,
        home_or_away TEXT NOT NULL,
        place_text TEXT,
        place_parsed_url TEXT,
        source_import TEXT,
        created_by INTEGER,
        created_at DATETIME,
        updated_at DATETIME
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        comment TEXT,
        nickname_at_time TEXT,
        updated_at DATETIME,
        updated_by INTEGER,
        FOREIGN KEY(match_id) REFERENCES matches(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_id INTEGER,
        match_id INTEGER,
        user_id INTEGER,
        old_status TEXT,
        new_status TEXT,
        comment TEXT,
        changed_at DATETIME,
        changed_by INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS user_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        target_user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at DATETIME
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uploader_id INTEGER,
        source_text TEXT,
        row_count INTEGER,
        created_at DATETIME
    );
    """
]


def get_db_path() -> str:
    DEFAULT_DB.parent.mkdir(exist_ok=True)
    return str(DEFAULT_DB)


def get_conn(path: str = None):
    p = path or get_db_path()
    conn = sqlite3.connect(p, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # set a busy timeout to avoid "database is locked" on concurrent writes
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def with_retry(func, retries: int = 5, base_delay: float = 0.05):
    """Run func() with retries on sqlite3.OperationalError containing 'locked'.

    func should be a callable with no arguments; the result will be returned.
    """
    import time
    import sqlite3

    for i in range(retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if 'locked' in msg or 'database is locked' in msg:
                if i == retries - 1:
                    raise
                time.sleep(base_delay * (2 ** i))
                continue
            raise


def init_db(path: str = None):
    p = path or get_db_path()
    conn = get_conn(p)
    try:
        # enable WAL for better concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        for sql in CREATE_TABLES_SQL:
            conn.executescript(sql)

        conn.commit()
    finally:
        conn.close()
