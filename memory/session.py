import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "nexus_sessions.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                query       TEXT    NOT NULL,
                agent       TEXT    NOT NULL,
                model       TEXT,
                result      TEXT,
                success     INTEGER NOT NULL DEFAULT 1,
                error_msg   TEXT,
                duration_ms INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date            TEXT PRIMARY KEY,
                total_runs      INTEGER DEFAULT 0,
                successful_runs INTEGER DEFAULT 0,
                failed_runs     INTEGER DEFAULT 0,
                agents_used     TEXT    DEFAULT '{}'
            )
        """)


def log_session(
    query: str,
    agent: str,
    model: str = None,
    result: str = None,
    success: bool = True,
    error_msg: str = None,
    duration_ms: int = None
) -> int:
    """Log a pipeline session. Returns the new session id."""
    init_db()
    timestamp = datetime.now().isoformat()
    date = datetime.now().strftime("%Y-%m-%d")

    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sessions
               (timestamp, query, agent, model, result, success, error_msg, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, query[:500], agent, model,
             result[:1000] if result else None,
             int(success), error_msg, duration_ms)
        )
        session_id = cur.lastrowid

        # Upsert daily stats
        row = conn.execute(
            "SELECT * FROM daily_stats WHERE date = ?", (date,)
        ).fetchone()

        if row:
            agents = json.loads(row["agents_used"])
            agents[agent] = agents.get(agent, 0) + 1
            conn.execute(
                """UPDATE daily_stats SET
                   total_runs = total_runs + 1,
                   successful_runs = successful_runs + ?,
                   failed_runs = failed_runs + ?,
                   agents_used = ?
                   WHERE date = ?""",
                (int(success), int(not success), json.dumps(agents), date)
            )
        else:
            conn.execute(
                """INSERT INTO daily_stats
                   (date, total_runs, successful_runs, failed_runs, agents_used)
                   VALUES (?, 1, ?, ?, ?)""",
                (date, int(success), int(not success), json.dumps({agent: 1}))
            )

    return session_id


def get_recent_sessions(limit: int = 10) -> list:
    """Return the N most recent sessions."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_daily_stats(days: int = 7) -> list:
    """Return daily stats for the last N days."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM daily_stats
               ORDER BY date DESC LIMIT ?""", (days,)
        ).fetchall()
    return [dict(r) for r in rows]


def print_summary():
    """Print a quick stats summary to terminal."""
    stats = get_daily_stats(7)
    if not stats:
        print("No sessions recorded yet.")
        return
    print("\n=== Nexus Session Stats (last 7 days) ===")
    for row in stats:
        agents = json.loads(row["agents_used"])
        agent_str = ", ".join(f"{k}:{v}" for k, v in agents.items())
        print(
            f"  {row['date']} | runs={row['total_runs']} "
            f"ok={row['successful_runs']} fail={row['failed_runs']} "
            f"| agents: {agent_str}"
        )
