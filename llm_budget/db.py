"""SQLite database for budget tracking and spend logging."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DB_DIR = Path.home() / ".llm-budget"
DB_PATH = DB_DIR / "budget.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a connection to the budget database."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS budgets (
            agent       TEXT PRIMARY KEY,
            daily_usd   REAL DEFAULT 0,
            monthly_usd REAL DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS spend_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent        TEXT NOT NULL,
            model        TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cost_usd     REAL NOT NULL,
            logged_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_spend_agent_date
            ON spend_log(agent, logged_at);
    """)
    conn.commit()


# --- Budget CRUD ---

def set_budget(
    conn: sqlite3.Connection,
    agent: str,
    daily: Optional[float] = None,
    monthly: Optional[float] = None,
) -> dict:
    """Set or update budget for an agent. Returns the budget row."""
    existing = conn.execute(
        "SELECT * FROM budgets WHERE agent = ?", (agent,)
    ).fetchone()

    if existing:
        updates = []
        params = []
        if daily is not None:
            updates.append("daily_usd = ?")
            params.append(daily)
        if monthly is not None:
            updates.append("monthly_usd = ?")
            params.append(monthly)
        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(agent)
            conn.execute(
                f"UPDATE budgets SET {', '.join(updates)} WHERE agent = ?",
                params,
            )
    else:
        conn.execute(
            "INSERT INTO budgets (agent, daily_usd, monthly_usd) VALUES (?, ?, ?)",
            (agent, daily or 0, monthly or 0),
        )
    conn.commit()
    return dict(conn.execute(
        "SELECT * FROM budgets WHERE agent = ?", (agent,)
    ).fetchone())


def get_budget(conn: sqlite3.Connection, agent: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM budgets WHERE agent = ?", (agent,)
    ).fetchone()
    return dict(row) if row else None


def list_agents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM budgets ORDER BY agent").fetchall()
    return [dict(r) for r in rows]


def delete_agent(conn: sqlite3.Connection, agent: str) -> bool:
    cur = conn.execute("DELETE FROM budgets WHERE agent = ?", (agent,))
    conn.execute("DELETE FROM spend_log WHERE agent = ?", (agent,))
    conn.commit()
    return cur.rowcount > 0


# --- Spend logging ---

def log_spend(
    conn: sqlite3.Connection,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> dict:
    """Log a spend event. Returns the inserted row."""
    total = input_tokens + output_tokens
    conn.execute(
        """INSERT INTO spend_log
           (agent, model, input_tokens, output_tokens, total_tokens, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (agent, model, input_tokens, output_tokens, total, cost_usd),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM spend_log WHERE id = last_insert_rowid()"
    ).fetchone()
    return dict(row)


def get_daily_spend(conn: sqlite3.Connection, agent: str) -> float:
    """Total spend for agent today (UTC)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = conn.execute(
        """SELECT COALESCE(SUM(cost_usd), 0) as total
           FROM spend_log
           WHERE agent = ? AND date(logged_at) = ?""",
        (agent, today),
    ).fetchone()
    return row["total"]


def get_monthly_spend(conn: sqlite3.Connection, agent: str) -> float:
    """Total spend for agent this month (UTC)."""
    month_start = datetime.utcnow().strftime("%Y-%m-01")
    row = conn.execute(
        """SELECT COALESCE(SUM(cost_usd), 0) as total
           FROM spend_log
           WHERE agent = ? AND date(logged_at) >= ?""",
        (agent, month_start),
    ).fetchone()
    return row["total"]


def get_history(
    conn: sqlite3.Connection,
    agent: str,
    days: int = 7,
) -> list[dict]:
    """Get spend history for an agent over the past N days."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT * FROM spend_log
           WHERE agent = ? AND date(logged_at) >= ?
           ORDER BY logged_at DESC""",
        (agent, since),
    ).fetchall()
    return [dict(r) for r in rows]


def reset_daily(conn: sqlite3.Connection, agent: str) -> int:
    """Delete today's spend entries for an agent. Returns count deleted."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cur = conn.execute(
        "DELETE FROM spend_log WHERE agent = ? AND date(logged_at) = ?",
        (agent, today),
    )
    conn.commit()
    return cur.rowcount


def reset_monthly(conn: sqlite3.Connection, agent: str) -> int:
    """Delete this month's spend entries for an agent. Returns count deleted."""
    month_start = datetime.utcnow().strftime("%Y-%m-01")
    cur = conn.execute(
        "DELETE FROM spend_log WHERE agent = ? AND date(logged_at) >= ?",
        (agent, month_start),
    )
    conn.commit()
    return cur.rowcount
