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
                end_date    TEXT,
                time        TEXT,
                end_time    TEXT,
                all_day     INTEGER DEFAULT 1,
                notes       TEXT,
                color       TEXT    DEFAULT '#89b4fa',
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate databases created before end_date was added
        try:
            c.execute("ALTER TABLE events ADD COLUMN end_date TEXT")
        except Exception:
            pass


# An event overlaps a date range when it starts on or before the range end
# AND it ends on or after the range start (end_date defaults to date for single-day).
_OVERLAP = "date <= :end AND COALESCE(end_date, date) >= :start"


def get_events_for_date(d: date):
    iso = d.isoformat()
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events WHERE {_OVERLAP} ORDER BY time",
            {"start": iso, "end": iso}
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_range(start: date, end: date):
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events WHERE {_OVERLAP} ORDER BY date, time",
            {"start": start.isoformat(), "end": end.isoformat()}
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_month(year, month):
    import calendar as _cal
    last = _cal.monthrange(year, month)[1]
    start = date(year, month, 1).isoformat()
    end = date(year, month, last).isoformat()
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events WHERE {_OVERLAP} ORDER BY date, time",
            {"start": start, "end": end}
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_year(year):
    start = date(year, 1, 1).isoformat()
    end = date(year, 12, 31).isoformat()
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events WHERE {_OVERLAP} ORDER BY date, time",
            {"start": start, "end": end}
        ).fetchall()
    return [dict(r) for r in rows]


def add_event(title, date, end_date=None, time=None, end_time=None,
              all_day=True, notes=None, color="#89b4fa"):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events "
            "(title, date, end_date, time, end_time, all_day, notes, color) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (title, date, end_date, time, end_time,
             1 if all_day else 0, notes, color)
        )
        return cur.lastrowid


def update_event(event_id, **kwargs):
    if not kwargs:
        return
    kwargs.pop("id", None)
    kwargs.pop("created_at", None)
    if "all_day" in kwargs:
        kwargs["all_day"] = 1 if kwargs["all_day"] else 0
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with _conn() as c:
        c.execute(f"UPDATE events SET {sets} WHERE id=?",
                  [*kwargs.values(), event_id])


def delete_event(event_id):
    with _conn() as c:
        c.execute("DELETE FROM events WHERE id=?", (event_id,))
