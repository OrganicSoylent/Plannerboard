from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QRadioButton, QSpinBox,
    QDateEdit, QTimeEdit, QComboBox, QDialogButtonBox, QWidget, QFrame,
)
from PyQt6.QtCore import QDate, QTime
from PyQt6.QtGui import QFont
from plannerboard.ui import theme


class EventDetailDialog(QDialog):
    """Read-only event detail view with an Edit button."""

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        self._event = event
        self._edited = False
        self._deleted = False
        self.setWindowTitle("Event Details")
        self.setMinimumWidth(380)
        self._build()

    def _build(self):
        from plannerboard.data import events_db as _db
        self._db = _db

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Color dot + title
        title_row = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(
            f"background:{self._event.get('color', theme.BLUE)};border-radius:7px;"
        )
        title_row.addWidget(dot)
        title_lbl = QLabel(self._event.get("title", ""))
        title_lbl.setFont(QFont("Sans", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color:{theme.TEXT};background:transparent;")
        title_lbl.setWordWrap(True)
        title_row.addWidget(title_lbl, 1)
        layout.addLayout(title_row)

        # Date
        d = date.fromisoformat(self._event["date"])
        date_str = d.strftime("%A, %-d %B %Y")
        if self._event.get("end_date") and self._event["end_date"] != self._event["date"]:
            ed = date.fromisoformat(self._event["end_date"])
            date_str += f" – {ed.strftime('%-d %B %Y')}"
        layout.addWidget(self._sub(f"📅 {date_str}"))

        # Time
        if not self._event.get("all_day") and self._event.get("time"):
            t = self._event["time"][:5]
            et = (self._event.get("end_time") or "")[:5]
            time_str = f"{t} – {et}" if et else t
            layout.addWidget(self._sub(f"⏰ {time_str}"))

        # Reminders (loaded from the reminders table)
        if self._event.get("id"):
            _REMINDER_LABELS = {
                0: "At event time", 5: "5 min before", 10: "10 min before",
                15: "15 min before", 30: "30 min before", 60: "1 hour before",
                120: "2 hours before", 1440: "1 day before",
            }
            for r in self._db.get_reminders_for_event(self._event["id"]):
                m = int(r["minutes"])
                lbl = _REMINDER_LABELS.get(m, f"{m} min before")
                layout.addWidget(self._sub(f"🔔 {lbl}"))

        # Notes
        notes = (self._event.get("notes") or "").strip()
        if notes:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color:{theme.BORDER};")
            layout.addWidget(sep)
            notes_lbl = QLabel(notes)
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet(
                f"color:{theme.SUBTEXT};font-size:9pt;background:transparent;"
            )
            layout.addWidget(notes_lbl)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._on_edit)
        btn_row.addWidget(edit_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _sub(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{theme.SUBTEXT};font-size:10pt;background:transparent;")
        return lbl

    def _on_edit(self):
        dlg = EventDialog(self, event=self._event)
        if dlg.exec():
            if dlg.deleted:
                self._db.delete_event(self._event["id"])
                self._deleted = True
            else:
                self._db.update_event(self._event["id"], **dlg.get_data())
                self._edited = True
            self.accept()

    @property
    def edited(self) -> bool:
        return self._edited

    @property
    def deleted(self) -> bool:
        return self._deleted


class EventDialog(QDialog):
    def __init__(self, parent=None, initial_date=None, event=None):
        super().__init__(parent)
        self._event = event
        self.setWindowTitle("Edit Event" if event else "New Event")
        self.setMinimumWidth(400)
        self._deleted = False
        self._build(initial_date or date.today(), event)

    def _build(self, initial_date, event):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Title ─────────────────────────────────────────────────────────
        layout.addWidget(QLabel("Title"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Event title…")
        layout.addWidget(self.title_edit)

        # ── Start date ────────────────────────────────────────────────────
        layout.addWidget(QLabel("Start date"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate(initial_date.year, initial_date.month, initial_date.day))
        layout.addWidget(self.date_edit)

        # ── Multi-day toggle + end date ────────────────────────────────────
        self.multiday_cb = QCheckBox("Multi-day event")
        layout.addWidget(self.multiday_cb)

        self._end_date_row = QWidget()
        edr = QVBoxLayout(self._end_date_row)
        edr.setContentsMargins(0, 0, 0, 0)
        edr.addWidget(QLabel("End date"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.end_date_edit.setDate(self.date_edit.date())
        edr.addWidget(self.end_date_edit)
        self._end_date_row.setVisible(False)
        layout.addWidget(self._end_date_row)

        self.multiday_cb.toggled.connect(self._end_date_row.setVisible)
        self.multiday_cb.toggled.connect(self._sync_end_date)
        self.date_edit.dateChanged.connect(self._on_start_changed)

        # ── Recurrence (new events only) ──────────────────────────────────
        if not event:
            self._repeat_cb = QCheckBox("Repeat this event")
            layout.addWidget(self._repeat_cb)

            self._recur_section = QWidget()
            self._recur_section.setVisible(False)
            rl = QVBoxLayout(self._recur_section)
            rl.setContentsMargins(12, 2, 0, 2)
            rl.setSpacing(6)

            interval_row = QHBoxLayout()
            interval_row.addWidget(QLabel("Interval:"))
            self._interval_cb = QComboBox()
            for lbl, code in [("Daily", "daily"), ("Weekly", "weekly"),
                               ("Every 2 weeks", "biweekly"),
                               ("Monthly", "monthly"), ("Yearly", "yearly")]:
                self._interval_cb.addItem(lbl, code)
            interval_row.addWidget(self._interval_cb)
            interval_row.addStretch()
            rl.addLayout(interval_row)

            count_row = QHBoxLayout()
            self._count_radio = QRadioButton("After")
            self._count_radio.setChecked(True)
            self._count_spin = QSpinBox()
            self._count_spin.setRange(2, 500)
            self._count_spin.setValue(4)
            count_row.addWidget(self._count_radio)
            count_row.addWidget(self._count_spin)
            count_row.addWidget(QLabel("occurrences"))
            count_row.addStretch()
            rl.addLayout(count_row)

            until_row = QHBoxLayout()
            self._until_radio = QRadioButton("Until")
            self._until_date = QDateEdit()
            self._until_date.setCalendarPopup(True)
            self._until_date.setDisplayFormat("dd.MM.yyyy")
            self._until_date.setDate(self.date_edit.date().addMonths(3))
            self._until_date.setEnabled(False)
            until_row.addWidget(self._until_radio)
            until_row.addWidget(self._until_date)
            until_row.addStretch()
            rl.addLayout(until_row)

            self._count_radio.toggled.connect(self._count_spin.setEnabled)
            self._count_radio.toggled.connect(lambda on: self._until_date.setEnabled(not on))
            self._repeat_cb.toggled.connect(self._recur_section.setVisible)
            layout.addWidget(self._recur_section)
        else:
            self._repeat_cb = None

        # ── All-day toggle ────────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{theme.BORDER};")
        layout.addWidget(div)

        self.all_day_cb = QCheckBox("All-day event")
        self.all_day_cb.setChecked(True)
        layout.addWidget(self.all_day_cb)

        # ── Time row ──────────────────────────────────────────────────────
        self.time_row = QWidget()
        tr = QHBoxLayout(self.time_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.addWidget(QLabel("From"))
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(9, 0))
        tr.addWidget(self.start_time)
        tr.addWidget(QLabel("To"))
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime(10, 0))
        tr.addWidget(self.end_time)
        layout.addWidget(self.time_row)
        self.all_day_cb.toggled.connect(self.time_row.setHidden)
        self.time_row.setHidden(True)
        self.start_time.timeChanged.connect(self._sync_end_time)

        # ── Reminders (multiple checkboxes, hidden for all-day events) ────
        self._reminder_section = QWidget()
        rs = QVBoxLayout(self._reminder_section)
        rs.setContentsMargins(0, 0, 0, 0)
        rs.setSpacing(4)
        rs.addWidget(QLabel("Reminders"))

        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(4)
        self._reminder_checks: list[tuple[QCheckBox, int]] = []
        _opts = [
            (0,    "At event time"),
            (5,    "5 minutes before"),
            (10,   "10 minutes before"),
            (15,   "15 minutes before"),
            (30,   "30 minutes before"),
            (60,   "1 hour before"),
            (120,  "2 hours before"),
            (1440, "1 day before"),
        ]
        for idx, (minutes, label) in enumerate(_opts):
            cb = QCheckBox(label)
            self._reminder_checks.append((cb, minutes))
            gl.addWidget(cb, idx // 2, idx % 2)
        rs.addWidget(grid)
        layout.addWidget(self._reminder_section)
        self.all_day_cb.toggled.connect(self._reminder_section.setHidden)
        self._reminder_section.setHidden(True)

        # ── Color picker ──────────────────────────────────────────────────
        layout.addWidget(QLabel("Color"))
        color_row = QHBoxLayout()
        self._color_btns: list[tuple[QPushButton, str]] = []
        self._selected_color = theme.BLUE
        for c in theme.EVENT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.clicked.connect(lambda _, col=c: self._pick_color(col))
            self._color_btns.append((btn, c))
            color_row.addWidget(btn)
        color_row.addStretch()
        layout.addLayout(color_row)
        self._pick_color(theme.BLUE)

        # ── Notes ─────────────────────────────────────────────────────────
        layout.addWidget(QLabel("Notes"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes…")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        # ── Buttons ───────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        if event:
            del_btn = btns.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
            del_btn.clicked.connect(self._delete)
        layout.addWidget(btns)

        # ── Populate when editing ─────────────────────────────────────────
        if event:
            self.title_edit.setText(event.get("title", ""))
            sd = date.fromisoformat(event["date"])
            self.date_edit.setDate(QDate(sd.year, sd.month, sd.day))

            if event.get("end_date") and event["end_date"] != event["date"]:
                ed = date.fromisoformat(event["end_date"])
                self.end_date_edit.setDate(QDate(ed.year, ed.month, ed.day))
                self.multiday_cb.setChecked(True)

            all_day = bool(event.get("all_day", True))
            self.all_day_cb.setChecked(all_day)
            if event.get("time"):
                h, m = (int(x) for x in event["time"].split(":"))
                self.start_time.setTime(QTime(h, m))
            if event.get("end_time"):
                h, m = (int(x) for x in event["end_time"].split(":"))
                self.end_time.setTime(QTime(h, m))
            self.notes_edit.setPlainText(event.get("notes") or "")
            self._pick_color(event.get("color", theme.BLUE))
            if event.get("id"):
                from plannerboard.data import events_db as _edb
                existing = {r["minutes"] for r in _edb.get_reminders_for_event(event["id"])}
                for cb, m in self._reminder_checks:
                    cb.setChecked(m in existing)

    # ── internal helpers ──────────────────────────────────────────────────

    def _sync_end_time(self, qt):
        new_end = qt.addSecs(3600)
        self.end_time.setTime(new_end)

    def _sync_end_date(self, checked):
        if checked:
            self.end_date_edit.setDate(self.date_edit.date())

    def _on_start_changed(self, qd):
        if not self.multiday_cb.isChecked():
            self.end_date_edit.setDate(qd)
        elif self.end_date_edit.date() < qd:
            self.end_date_edit.setDate(qd)

    def _pick_color(self, color):
        self._selected_color = color
        for btn, c in self._color_btns:
            border = theme.TEXT if c == color else "transparent"
            btn.setStyleSheet(
                f"background:{c};border-radius:4px;border:2px solid {border};"
            )

    def _accept(self):
        if not self.title_edit.text().strip():
            self.title_edit.setPlaceholderText("⚠ Title required")
            return
        self.accept()

    def _delete(self):
        self._deleted = True
        self.accept()

    # ── public ───────────────────────────────────────────────────────────

    @property
    def deleted(self):
        return self._deleted

    def get_data(self):
        qsd = self.date_edit.date()
        all_day = self.all_day_cb.isChecked()

        end_date = None
        if self.multiday_cb.isChecked():
            qed = self.end_date_edit.date()
            end_date = date(qed.year(), qed.month(), qed.day()).isoformat()

        reminders = (
            [] if all_day
            else [m for cb, m in self._reminder_checks if cb.isChecked()]
        )

        recurrence = None
        if self._repeat_cb is not None and self._repeat_cb.isChecked():
            recurrence = {
                "interval": self._interval_cb.currentData(),
                "mode": "count" if self._count_radio.isChecked() else "until",
            }
            if self._count_radio.isChecked():
                recurrence["count"] = self._count_spin.value()
            else:
                qud = self._until_date.date()
                recurrence["end_date"] = date(qud.year(), qud.month(), qud.day()).isoformat()

        return {
            "title": self.title_edit.text().strip(),
            "date": date(qsd.year(), qsd.month(), qsd.day()).isoformat(),
            "end_date": end_date,
            "time": None if all_day else self.start_time.time().toString("HH:mm"),
            "end_time": None if all_day else self.end_time.time().toString("HH:mm"),
            "all_day": all_day,
            "notes": self.notes_edit.toPlainText().strip() or None,
            "color": self._selected_color,
            "reminders": reminders,
            "recurrence": recurrence,
        }
