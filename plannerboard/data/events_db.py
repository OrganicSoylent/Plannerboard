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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title           TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                end_date        TEXT,
                time            TEXT,
                end_time        TEXT,
                all_day         INTEGER DEFAULT 1,
                notes           TEXT,
                color           TEXT    DEFAULT '#89b4fa',
                reminder        INTEGER,
                reminder_fired  TEXT,
                created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col in ("end_date TEXT", "reminder INTEGER", "reminder_fired TEXT",
                    "series_id TEXT"):
            try:
                c.execute(f"ALTER TABLE events ADD COLUMN {col}")
            except Exception:
                pass

        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id    INTEGER NOT NULL,
                minutes     INTEGER NOT NULL,
                fired_key   TEXT
            )
        """)
        # One-time migration: move old single-reminder data into the new table
        try:
            old_rows = c.execute(
                "SELECT id, reminder, reminder_fired FROM events WHERE reminder IS NOT NULL"
            ).fetchall()
            for row in old_rows:
                exists = c.execute(
                    "SELECT 1 FROM reminders WHERE event_id=? AND minutes=?",
                    (row[0], row[1])
                ).fetchone()
                if not exists:
                    c.execute(
                        "INSERT INTO reminders (event_id, minutes, fired_key) VALUES (?,?,?)",
                        (row[0], row[1], row[2])
                    )
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


def get_reminders_for_event(event_id) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM reminders WHERE event_id=? ORDER BY minutes",
            (event_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def set_reminders_for_event(event_id, minutes_list: list):
    with _conn() as c:
        c.execute("DELETE FROM reminders WHERE event_id=?", (event_id,))
        for m in minutes_list:
            c.execute(
                "INSERT INTO reminders (event_id, minutes) VALUES (?,?)",
                (event_id, int(m))
            )


def add_event(title, date, end_date=None, time=None, end_time=None,
              all_day=True, notes=None, color="#89b4fa", reminders=None,
              series_id=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events "
            "(title, date, end_date, time, end_time, all_day, notes, color, series_id) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (title, date, end_date, time, end_time,
             1 if all_day else 0, notes, color, series_id)
        )
        event_id = cur.lastrowid
    if reminders:
        set_reminders_for_event(event_id, reminders)
    return event_id


def update_event(event_id, **kwargs):
    reminders = kwargs.pop("reminders", None)
    # Strip fields not in the events table or handled separately
    for key in ("id", "created_at", "reminder", "reminder_fired",
                "series_id", "recurrence"):
        kwargs.pop(key, None)
    if "all_day" in kwargs:
        kwargs["all_day"] = 1 if kwargs["all_day"] else 0
    if kwargs:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        with _conn() as c:
            c.execute(f"UPDATE events SET {sets} WHERE id=?",
                      [*kwargs.values(), event_id])
    if reminders is not None:
        set_reminders_for_event(event_id, reminders)


def get_due_reminders() -> list:
    """Return (reminder_id, event_dict, fired_key) for reminders now due but not yet fired."""
    from datetime import datetime, timedelta
    now = datetime.now()
    window_start = now - timedelta(hours=2)
    today = now.date().isoformat()
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    with _conn() as c:
        rows = c.execute("""
            SELECT r.id        AS reminder_id,
                   r.minutes   AS reminder_minutes,
                   r.fired_key AS reminder_fired_key,
                   e.id, e.title, e.date, e.time, e.end_time, e.notes, e.color
            FROM reminders r
            JOIN events e ON r.event_id = e.id
            WHERE e.time IS NOT NULL AND e.all_day = 0
              AND e.date BETWEEN ? AND ?
        """, (today, tomorrow)).fetchall()
    due = []
    for row in [dict(r) for r in rows]:
        try:
            ev_dt = datetime.fromisoformat(f"{row['date']}T{row['time']}")
        except ValueError:
            continue
        reminder_dt = ev_dt - timedelta(minutes=int(row["reminder_minutes"]))
        fired_key = f"{row['date']}T{row['time']}R{row['reminder_minutes']}"
        if window_start <= reminder_dt <= now and row["reminder_fired_key"] != fired_key:
            event = {k: row[k] for k in ("id", "title", "date", "time", "end_time", "notes", "color")}
            due.append((row["reminder_id"], event, fired_key))
    return due


def mark_reminder_fired(reminder_id, fired_key):
    with _conn() as c:
        c.execute("UPDATE reminders SET fired_key=? WHERE id=?", (fired_key, reminder_id))


def delete_event(event_id):
    with _conn() as c:
        c.execute("DELETE FROM reminders WHERE event_id=?", (event_id,))
        c.execute("DELETE FROM events WHERE id=?", (event_id,))
