import sqlite3
from datetime import datetime
from typing import Optional

SESSION_DB = "aura_session.db"

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(SESSION_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_session_db() -> None:
    """Create tables on first run."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            timestamp  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS journals (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            entry      TEXT NOT NULL,
            phase      TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS preferences (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS health_data (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type     TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            value         REAL,
            metadata      TEXT
        );
    """)
    conn.commit()
    conn.close()
def save_message(role: str, content: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO chat_history (role, content, timestamp) VALUES (?,?,?)",
        (role, content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

def load_chat_history(limit: int = 50) -> list[dict]:
    """Returns the last `limit` messages, oldest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM chat_history ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
        for r in reversed(rows)
    ]

def clear_chat_history() -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()

def save_journal_entry(entry: str, phase: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO journals (timestamp, entry, phase) VALUES (?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), entry, phase),
    )
    conn.commit()
    conn.close()

def get_journals() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT timestamp, entry, phase FROM journals ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [
        {"timestamp": r["timestamp"], "entry": r["entry"], "phase": r["phase"]}
        for r in rows
    ]

def get_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_preference(key: str, value: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO preferences (key, value) VALUES (?,?)",
        (key, value),
    )
    conn.commit()
    conn.close()

def log_health_metric(data_type: str, value: float, metadata: str = "") -> None:
    """Allow user to manually log a health metric (e.g., mood, pain level)."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO health_data (data_type, timestamp, value, metadata) VALUES (?,?,?,?)",
        (data_type, datetime.now().isoformat(), value, metadata),
    )
    conn.commit()
    conn.close()

def get_health_metrics(data_type: str, limit: int = 30) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT timestamp, value, metadata FROM health_data WHERE data_type = ? ORDER BY timestamp DESC LIMIT ?",
        (data_type, limit),
    ).fetchall()
    conn.close()
    return [
        {"timestamp": r["timestamp"], "value": r["value"], "metadata": r["metadata"]}
        for r in rows
    ]

init_session_db()
