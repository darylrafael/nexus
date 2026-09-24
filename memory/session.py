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

    try:
        export_telemetry_json()
    except Exception:
        pass

    return session_id


def export_telemetry_json(output_path: Path = None) -> dict:
    """
    Export execution telemetry stats and recent sessions to a self-contained
    JSON artifact (runs/global/telemetry.json) for cloud dashboard deployment.
    """
    init_db()
    today_prefix = datetime.now().strftime("%Y-%m-%d")

    with _get_conn() as conn:
        total_row = conn.execute("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_runs,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_runs,
                AVG(duration_ms) as avg_duration_ms
            FROM sessions
        """).fetchone()

        total = total_row["total_runs"] or 0
        successful = total_row["successful_runs"] or 0
        failed = total_row["failed_runs"] or 0
        avg_ms = round(total_row["avg_duration_ms"] or 0)
        rate = f"{(successful / total * 100):.1f}" if total > 0 else "0.0"

        runs_today_row = conn.execute(
            "SELECT COUNT(*) as runs_today FROM sessions WHERE timestamp LIKE ?",
            (f"{today_prefix}%",)
        ).fetchone()
        runs_today = runs_today_row["runs_today"] or 0

        agent_rows = conn.execute("""
            SELECT 
                agent,
                COUNT(*) as total_calls,
                ROUND(AVG(duration_ms), 1) as avg_duration_ms,
                ROUND(SUM(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) as success_rate_pct,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
            FROM sessions
            GROUP BY agent
            ORDER BY total_calls DESC
        """).fetchall()
        agent_breakdown = [dict(r) for r in agent_rows]

        session_rows = conn.execute("""
            SELECT id, timestamp, query, agent, model, result, success, error_msg, duration_ms
            FROM sessions
            ORDER BY id DESC
            LIMIT 50
        """).fetchall()
        sessions_list = [dict(r) for r in session_rows]

    payload = {
        "stats": {
            "totalRuns": total,
            "successfulRuns": successful,
            "failedRuns": failed,
            "successRate": rate,
            "avgDurationMs": avg_ms,
            "runsToday": runs_today
        },
        "agentBreakdown": agent_breakdown,
        "sessions": sessions_list,
        "exported_at": datetime.now().isoformat()
    }

    if output_path is None:
        runs_dir = Path(__file__).parent.parent / "runs" / "global"
        runs_dir.mkdir(parents=True, exist_ok=True)
        output_path = runs_dir / "telemetry.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[session] WARN - Failed to export telemetry.json: {e}")

    return payload


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
