import sqlite3
from datetime import date
from plannerboard.config import DATA_DIR

_DB = DATA_DIR / "events.db"


def _conn():
    c = sqlite3.connect(_DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                time        TEXT,
                end_time    TEXT,
                all_day     INTEGER DEFAULT 1,
                notes       TEXT,
                color       TEXT    DEFAULT '#89b4fa',
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_events_for_date(d: date):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE date=? ORDER BY time",
            (d.isoformat(),)
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_range(start: date, end: date):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY date, time",
            (start.isoformat(), end.isoformat())
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_month(year, month):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE strftime('%Y-%m', date)=? ORDER BY date, time",
            (f"{year:04d}-{month:02d}",)
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_year(year):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE strftime('%Y', date)=? ORDER BY date, time",
            (str(year),)
        ).fetchall()
    return [dict(r) for r in rows]


def add_event(title, date_str, time_str=None, end_time=None,
              all_day=True, notes=None, color="#89b4fa"):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events (title,date,time,end_time,all_day,notes,color) "
            "VALUES (?,?,?,?,?,?,?)",
            (title, date_str, time_str, end_time, 1 if all_day else 0, notes, color)
        )
        return cur.lastrowid


def update_event(event_id, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with _conn() as c:
        c.execute(f"UPDATE events SET {sets} WHERE id=?",
                  [*kwargs.values(), event_id])


def delete_event(event_id):
    with _conn() as c:
        c.execute("DELETE FROM events WHERE id=?", (event_id,))
