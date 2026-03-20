
import sqlite3
from datetime import datetime
from typing import Optional

SESSION_DB = "aura_session.db"

try:
    from realtime_journal_indexer import index_journal_entry
    REALTIME_INDEXING_ENABLED = True
    print("✅ Real-time journal indexing enabled")
except ImportError:
    REALTIME_INDEXING_ENABLED = False
    print("⚠️  Real-time indexing disabled (realtime_journal_indexer.py not found)")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(SESSION_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_session_db() -> None:
    """Create tables on first run and migrate if needed."""
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
            phase      TEXT DEFAULT '',
            indexed    INTEGER DEFAULT 0
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
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(journals)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'indexed' not in columns:
            print("[SESSION] ⚡ Auto-migrating: Adding 'indexed' column...")
            cursor.execute("ALTER TABLE journals ADD COLUMN indexed INTEGER DEFAULT 0")
            cursor.execute("UPDATE journals SET indexed = 1")
            print(f"[SESSION] ✅ Migration complete: Marked {cursor.rowcount} existing entries")
    except Exception as e:
        print(f"[SESSION] ⚠️  Auto-migration check failed: {e}")
    
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
    """Save journal entry and index it in real-time."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO journals (timestamp, entry, phase, indexed) VALUES (?,?,?,?)",
        (timestamp, entry, phase, 0),
    )
    entry_id = cursor.lastrowid
    conn.commit()

    if REALTIME_INDEXING_ENABLED:
        try:
            print(f"[SESSION] 🔄 Indexing journal entry in real-time...")
            success = index_journal_entry(entry, timestamp)
            if success:
                conn.execute(
                    "UPDATE journals SET indexed = 1 WHERE id = ?",
                    (entry_id,)
                )
                conn.commit()
                print(f"[SESSION] ✅ Entry indexed and marked")
            else:
                print(f"[SESSION] ⚠️  Indexing failed, entry saved but not searchable yet")
        except Exception as e:
            print(f"[SESSION] ❌ Real-time indexing error: {e}")
    else:
        print(f"[SESSION] ⚠️  Entry saved but not indexed (indexing disabled)")
    
    conn.close()

def get_journals(limit: int = None, include_unindexed: bool = True) -> list[dict]:
    """Get journal entries, optionally filtered by indexing status."""
    conn = _get_conn()
    if limit:
        if include_unindexed:
            query = "SELECT timestamp, entry, phase, indexed FROM journals ORDER BY timestamp DESC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()
        else:
            query = "SELECT timestamp, entry, phase, indexed FROM journals WHERE indexed = 1 ORDER BY timestamp DESC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()
    else:
        if include_unindexed:
            rows = conn.execute(
                "SELECT timestamp, entry, phase, indexed FROM journals ORDER BY timestamp DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT timestamp, entry, phase, indexed FROM journals WHERE indexed = 1 ORDER BY timestamp DESC"
            ).fetchall()
    
    conn.close()
    return [
        {
            "timestamp": r["timestamp"], 
            "entry": r["entry"], 
            "phase": r["phase"],
            "indexed": bool(r["indexed"])
        }
        for r in rows
    ]

def get_todays_journals() -> list[dict]:
    """Get journal entries from today only."""
    conn = _get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    
    rows = conn.execute(
        "SELECT timestamp, entry, phase, indexed FROM journals WHERE timestamp LIKE ? ORDER BY timestamp DESC",
        (f"{today}%",)
    ).fetchall()    
    conn.close()
    return [
        {
            "timestamp": r["timestamp"], 
            "entry": r["entry"], 
            "phase": r["phase"],
            "indexed": bool(r["indexed"])
        }
        for r in rows
    ]

def get_recent_journals(hours: int = 24) -> list[dict]:
    """Get journal entries from the last N hours."""
    from datetime import timedelta
    
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    rows = conn.execute(
        "SELECT timestamp, entry, phase, indexed FROM journals WHERE timestamp >= ? ORDER BY timestamp DESC",
        (cutoff,)
    ).fetchall()
    
    conn.close()
    return [
        {
            "timestamp": r["timestamp"], 
            "entry": r["entry"], 
            "phase": r["phase"],
            "indexed": bool(r["indexed"])
        }
        for r in rows
    ]

def reindex_unindexed_entries() -> int:
    """Manually reindex any entries that failed to index."""
    if not REALTIME_INDEXING_ENABLED:
        print("[SESSION] ❌ Real-time indexing not available")
        return 0
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, timestamp, entry FROM journals WHERE indexed = 0"
    ).fetchall()
    count = 0
    for row in rows:
        try:
            success = index_journal_entry(row["entry"], row["timestamp"])
            if success:
                conn.execute("UPDATE journals SET indexed = 1 WHERE id = ?", (row["id"],))
                count += 1
        except Exception as e:
            print(f"[SESSION] Failed to index entry {row['id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"[SESSION] ✅ Reindexed {count} entries")
    return count

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
    """Allow user to manually log a health metric."""
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

if REALTIME_INDEXING_ENABLED:
    print("✅ Session manager ready with real-time journal indexing")
else:
    print("⚠️  Session manager ready (real-time indexing disabled)")
