from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QDateEdit, QTimeEdit,
    QDialogButtonBox, QWidget, QFrame,
)
from PyQt6.QtCore import QDate, QTime
from plannerboard.ui import theme


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

    # ── internal helpers ──────────────────────────────────────────────────

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

        return {
            "title": self.title_edit.text().strip(),
            "date": date(qsd.year(), qsd.month(), qsd.day()).isoformat(),
            "end_date": end_date,
            "time": None if all_day else self.start_time.time().toString("HH:mm"),
            "end_time": None if all_day else self.end_time.time().toString("HH:mm"),
            "all_day": all_day,
            "notes": self.notes_edit.toPlainText().strip() or None,
            "color": self._selected_color,
        }
