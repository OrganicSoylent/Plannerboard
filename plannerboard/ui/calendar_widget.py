import calendar
from datetime import date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QStackedWidget, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve

from plannerboard.ui.views.month_view import MonthView
from plannerboard.ui.views.week_view import WeekView
from plannerboard.ui.views.day_view import DayView
from plannerboard.ui.views.year_view import YearView
from plannerboard.ui.event_dialog import EventDialog, EventDetailDialog
from plannerboard.data import events_db
from plannerboard.data.holidays_service import get_holidays
from plannerboard.data.liturgical_service import get_liturgical_calendar
from plannerboard.ui import theme

VIEW_DAY = 0
VIEW_WEEK = 1
VIEW_MONTH = 2
VIEW_YEAR = 3


class CalendarWidget(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._view_idx = VIEW_MONTH
        self._current = date.today()
        self._holidays = {}
        self._loaded_hol_year = None
        self._liturgical: dict = {}
        self._loaded_lit_year: int | None = None
        self._liturgical_enabled: bool = config.get("liturgical_calendar", False)
        self._build_ui()
        self._load_holidays(self._current.year)
        self._load_liturgical(self._current.year)
        self._refresh()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background:{theme.SURFACE};")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        tl.setSpacing(4)

        # Prev / Today / Next
        self._btn_prev = QPushButton("‹")
        self._btn_today = QPushButton("Today")
        self._btn_next = QPushButton("›")
        for b in (self._btn_prev, self._btn_today, self._btn_next):
            b.setFixedHeight(28)
        self._btn_prev.setFixedWidth(28)
        self._btn_next.setFixedWidth(28)
        self._btn_prev.clicked.connect(self._go_prev)
        self._btn_today.clicked.connect(self._go_today)
        self._btn_next.clicked.connect(self._go_next)
        tl.addWidget(self._btn_prev)
        tl.addWidget(self._btn_today)
        tl.addWidget(self._btn_next)

        # Date label
        self._date_label = QLabel()
        self._date_label.setStyleSheet(f"color:{theme.TEXT};font-size:12pt;font-weight:bold;")
        tl.addWidget(self._date_label)
        tl.addStretch()

        # View selector
        self._view_btns = []
        for label, idx in [("Day", VIEW_DAY), ("Week", VIEW_WEEK),
                            ("Month", VIEW_MONTH), ("Year", VIEW_YEAR)]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _, i=idx: self._switch_view(i))
            self._view_btns.append(btn)
            tl.addWidget(btn)

        # Liturgical calendar toggle
        self._lit_btn = QPushButton("✝")
        self._lit_btn.setCheckable(True)
        self._lit_btn.setChecked(self._liturgical_enabled)
        self._lit_btn.setFixedSize(28, 28)
        self._lit_btn.setToolTip("Catholic Liturgical Calendar")
        self._lit_btn.clicked.connect(self._toggle_liturgical)
        tl.addWidget(self._lit_btn)

        root.addWidget(toolbar)
        root.setContentsMargins(0, 0, 0, 0)

        # Stacked views
        self._stack = QStackedWidget()
        self._day_view = DayView()
        self._week_view = WeekView()
        self._month_view = MonthView()
        self._year_view = YearView()

        self._stack.addWidget(self._day_view)    # 0
        self._stack.addWidget(self._week_view)   # 1
        self._stack.addWidget(self._month_view)  # 2
        self._stack.addWidget(self._year_view)   # 3

        root.addWidget(self._stack, 1)

        # ── Day-detail panel (slides open under the week view) ─────────────
        self._detail_day: date | None = None

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{theme.BORDER};background:{theme.BORDER};max-height:1px;")
        root.addWidget(sep)

        self._detail_panel = QWidget()
        self._detail_panel.setStyleSheet(f"background:{theme.BG};")
        dp_layout = QVBoxLayout(self._detail_panel)
        dp_layout.setContentsMargins(0, 0, 0, 0)
        dp_layout.setSpacing(0)
        self._detail_view = DayView()
        self._detail_view.slot_double_clicked.connect(self._new_event_timed)
        dp_layout.addWidget(self._detail_view)
        self._detail_panel.setMaximumHeight(0)
        root.addWidget(self._detail_panel)

        self._detail_anim = QPropertyAnimation(self._detail_panel, b"maximumHeight")
        self._detail_anim.setDuration(260)
        self._detail_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._detail_anim.finished.connect(self._on_detail_anim_done)

        # Connect double-click signals → event dialog
        self._day_view.slot_double_clicked.connect(self._new_event_timed)
        self._week_view.slot_double_clicked.connect(self._new_event_timed)
        self._month_view.date_double_clicked.connect(self._new_event_allday)
        self._month_view.event_double_clicked.connect(self._edit_event)
        self._year_view.month_double_clicked.connect(self._on_year_month_click)

        # Single click on any event → detail view
        self._day_view.event_clicked.connect(self._on_event_clicked)
        self._week_view.event_clicked.connect(self._on_event_clicked)
        self._month_view.event_clicked.connect(self._on_event_clicked)

        # Week-view day header click → sliding detail panel
        self._week_view.day_header_clicked.connect(self._on_day_header_clicked)

        self._switch_view(VIEW_MONTH)

    # ── view switching & navigation ────────────────────────────────────────

    def _switch_view(self, idx):
        self._view_idx = idx
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._view_btns):
            btn.setChecked(i == idx)
        if idx != VIEW_WEEK:
            self._collapse_detail()
        self._refresh()

    def _refresh(self):
        self._ensure_holidays(self._current.year)
        self._ensure_liturgical(self._current.year)
        self._update_date_label()
        hols = self._get_display_holidays()

        if self._view_idx == VIEW_DAY:
            evts = events_db.get_events_for_date(self._current)
            self._day_view.set_day(self._current, evts, hols)
            self._day_view.scroll_to_hour(8)

        elif self._view_idx == VIEW_WEEK:
            monday = self._current - timedelta(days=self._current.weekday())
            sunday = monday + timedelta(6)
            evts = events_db.get_events_for_range(monday, sunday)
            self._week_view.set_week(monday, evts, hols)
            self._week_view.scroll_to_hour(8)

        elif self._view_idx == VIEW_MONTH:
            evts = events_db.get_events_for_month(self._current.year, self._current.month)
            self._month_view.set_period(
                self._current.year, self._current.month, evts, hols
            )

        elif self._view_idx == VIEW_YEAR:
            evts = events_db.get_events_for_year(self._current.year)
            self._year_view.set_period(self._current.year, evts, hols)

    def _update_date_label(self):
        if self._view_idx == VIEW_DAY:
            label = self._current.strftime("%A, %-d %B %Y")
        elif self._view_idx == VIEW_WEEK:
            monday = self._current - timedelta(days=self._current.weekday())
            sunday = monday + timedelta(6)
            label = f"{monday.strftime('%-d %b')} – {sunday.strftime('%-d %b %Y')}"
        elif self._view_idx == VIEW_MONTH:
            label = self._current.strftime("%B %Y")
        else:
            label = str(self._current.year)
        self._date_label.setText(label)

    def _go_prev(self):
        if self._view_idx == VIEW_DAY:
            self._current -= timedelta(1)
        elif self._view_idx == VIEW_WEEK:
            self._current -= timedelta(7)
        elif self._view_idx == VIEW_MONTH:
            m = self._current.month - 1 or 12
            y = self._current.year - (1 if self._current.month == 1 else 0)
            self._current = self._current.replace(year=y, month=m, day=1)
        elif self._view_idx == VIEW_YEAR:
            self._current = self._current.replace(year=self._current.year - 1)
        self._refresh()

    def _go_next(self):
        if self._view_idx == VIEW_DAY:
            self._current += timedelta(1)
        elif self._view_idx == VIEW_WEEK:
            self._current += timedelta(7)
        elif self._view_idx == VIEW_MONTH:
            m = self._current.month % 12 + 1
            y = self._current.year + (1 if self._current.month == 12 else 0)
            self._current = self._current.replace(year=y, month=m, day=1)
        elif self._view_idx == VIEW_YEAR:
            self._current = self._current.replace(year=self._current.year + 1)
        self._refresh()

    def _go_today(self):
        self._current = date.today()
        self._refresh()

    # ── day detail panel ──────────────────────────────────────────────────

    def _on_day_header_clicked(self, d: date):
        if self._detail_day == d:
            # Same day clicked again → collapse
            self._collapse_detail()
        else:
            self._detail_day = d
            evts = events_db.get_events_for_date(d)
            self._detail_view.set_day(d, evts, self._holidays)
            if self._detail_panel.maximumHeight() < 300:
                self._detail_anim.stop()
                self._detail_anim.setStartValue(self._detail_panel.maximumHeight())
                self._detail_anim.setEndValue(300)
                self._detail_anim.start()

    def _collapse_detail(self):
        if self._detail_panel.maximumHeight() > 0:
            self._detail_anim.stop()
            self._detail_anim.setStartValue(self._detail_panel.maximumHeight())
            self._detail_anim.setEndValue(0)
            self._detail_anim.start()
        self._detail_day = None

    def _on_detail_anim_done(self):
        if self._detail_panel.maximumHeight() > 0:
            self._detail_view.scroll_to_hour(8)

    def _on_year_month_click(self, year, month):
        self._current = date(year, month, 1)
        self._switch_view(VIEW_MONTH)

    # ── liturgical calendar ────────────────────────────────────────────────

    def _toggle_liturgical(self):
        self._liturgical_enabled = self._lit_btn.isChecked()
        self._config.set("liturgical_calendar", self._liturgical_enabled)
        self._refresh()

    def _load_liturgical(self, year):
        self._liturgical = get_liturgical_calendar(year)
        self._loaded_lit_year = year

    def _ensure_liturgical(self, year):
        if year != self._loaded_lit_year:
            self._load_liturgical(year)

    def _get_display_holidays(self) -> dict:
        """Merge public holidays with liturgical feasts when enabled."""
        merged = dict(self._holidays)
        if self._liturgical_enabled:
            for d, name in self._liturgical.items():
                if d in merged:
                    merged[d] = f"{merged[d]} | ✝ {name}"
                else:
                    merged[d] = f"✝ {name}"
        return merged

    # ── holidays ──────────────────────────────────────────────────────────

    def _load_holidays(self, year):
        country = self._config.get("country", "DE")
        subdiv = self._config.get("subdivision") or None
        self._holidays = get_holidays(year, country, subdiv)
        self._loaded_hol_year = year

    def _ensure_holidays(self, year):
        if year != self._loaded_hol_year:
            self._load_holidays(year)

    # ── event creation ────────────────────────────────────────────────────

    def _on_event_clicked(self, event: dict):
        dlg = EventDetailDialog(event, self)
        if dlg.exec():
            if dlg.edited or dlg.deleted:
                self._refresh()

    def _new_event_allday(self, d: date):
        dlg = EventDialog(self, initial_date=d)
        if dlg.exec():
            self._create_events(dlg.get_data())
            self._refresh()

    def _new_event_timed(self, d: date, hour: int):
        dlg = EventDialog(self, initial_date=d)
        dlg.all_day_cb.setChecked(False)
        from PyQt6.QtCore import QTime
        dlg.start_time.setTime(QTime(hour, 0))
        dlg.end_time.setTime(QTime(min(hour + 1, 23), 0))
        if dlg.exec():
            self._create_events(dlg.get_data())
            self._refresh()

    def _edit_event(self, event: dict):
        dlg = EventDialog(self, event=event)
        if dlg.exec():
            if dlg.deleted:
                events_db.delete_event(event["id"])
            else:
                events_db.update_event(event["id"], **dlg.get_data())
            self._refresh()

    def _create_events(self, data: dict):
        """Create one or more event rows; expands recurrence when set."""
        import uuid
        recurrence = data.pop("recurrence", None)
        if not recurrence:
            events_db.add_event(**data)
            return
        series_id = str(uuid.uuid4())
        for iso_date in self._expand_recurrence(data["date"], recurrence):
            events_db.add_event(
                title=data["title"],
                date=iso_date,
                end_date=data.get("end_date"),
                time=data.get("time"),
                end_time=data.get("end_time"),
                all_day=data.get("all_day", True),
                notes=data.get("notes"),
                color=data.get("color", "#89b4fa"),
                reminders=data.get("reminders"),
                series_id=series_id,
            )

    @staticmethod
    def _expand_recurrence(start_iso: str, recurrence: dict) -> list:
        """Return a list of ISO date strings for each occurrence."""
        import calendar as _cal

        def _add_months(d, n):
            month = d.month + n
            year = d.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(d.day, _cal.monthrange(year, month)[1])
            return d.replace(year=year, month=month, day=day)

        _DELTAS = {"daily": timedelta(1), "weekly": timedelta(7), "biweekly": timedelta(14)}
        interval = recurrence["interval"]
        mode = recurrence["mode"]
        current = date.fromisoformat(start_iso)
        dates = []

        def _step(d):
            if interval in _DELTAS:
                return d + _DELTAS[interval]
            if interval == "monthly":
                return _add_months(d, 1)
            return _add_months(d, 12)  # yearly

        if mode == "count":
            for _ in range(recurrence.get("count", 4)):
                dates.append(current.isoformat())
                current = _step(current)
        else:
            end = date.fromisoformat(recurrence["end_date"])
            while current <= end:
                dates.append(current.isoformat())
                current = _step(current)

        return dates

    def reload(self):
        """Call after settings change (country, subdivision)."""
        self._load_holidays(self._current.year)
        self._refresh()
