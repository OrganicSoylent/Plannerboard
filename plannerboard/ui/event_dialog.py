from datetime import date, time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QCheckBox, QDateEdit, QTimeEdit,
    QComboBox, QDialogButtonBox, QWidget, QFrame,
)
from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtGui import QColor
from plannerboard.ui import theme


class ColorSwatch(QFrame):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(20, 20)
        self.setStyleSheet(
            f"background:{color};border-radius:4px;border:2px solid transparent;"
        )
        self.setToolTip(color)


class EventDialog(QDialog):
    def __init__(self, parent=None, initial_date=None, event=None):
        super().__init__(parent)
        self._event = event
        self.setWindowTitle("Edit Event" if event else "New Event")
        self.setMinimumWidth(380)
        self._build(initial_date, event)

    def _build(self, initial_date, event):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        layout.addWidget(QLabel("Title"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Event title…")
        layout.addWidget(self.title_edit)

        # Date
        layout.addWidget(QLabel("Date"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        d = initial_date or date.today()
        self.date_edit.setDate(QDate(d.year, d.month, d.day))
        layout.addWidget(self.date_edit)

        # All-day toggle
        self.all_day_cb = QCheckBox("All-day event")
        self.all_day_cb.setChecked(True)
        layout.addWidget(self.all_day_cb)

        # Time row
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

        # Color picker
        layout.addWidget(QLabel("Color"))
        color_row = QHBoxLayout()
        self._color_btns = []
        self._selected_color = theme.BLUE
        for c in theme.EVENT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(
                f"background:{c};border-radius:4px;border:2px solid transparent;"
            )
            btn.clicked.connect(lambda _, col=c: self._pick_color(col))
            self._color_btns.append((btn, c))
            color_row.addWidget(btn)
        color_row.addStretch()
        layout.addLayout(color_row)
        self._pick_color(theme.BLUE)

        # Notes
        layout.addWidget(QLabel("Notes"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes…")
        self.notes_edit.setMaximumHeight(80)
        layout.addWidget(self.notes_edit)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        if event:
            del_btn = btns.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
            del_btn.clicked.connect(self._delete)
        layout.addWidget(btns)

        # Populate if editing
        if event:
            self.title_edit.setText(event.get("title", ""))
            ed = date.fromisoformat(event["date"])
            self.date_edit.setDate(QDate(ed.year, ed.month, ed.day))
            all_day = bool(event.get("all_day", True))
            self.all_day_cb.setChecked(all_day)
            if event.get("time"):
                t = [int(x) for x in event["time"].split(":")]
                self.start_time.setTime(QTime(t[0], t[1]))
            if event.get("end_time"):
                t = [int(x) for x in event["end_time"].split(":")]
                self.end_time.setTime(QTime(t[0], t[1]))
            self.notes_edit.setPlainText(event.get("notes") or "")
            self._pick_color(event.get("color", theme.BLUE))

        self._deleted = False

    def _pick_color(self, color):
        self._selected_color = color
        for btn, c in self._color_btns:
            border = theme.TEXT if c == color else "transparent"
            btn.setStyleSheet(
                f"background:{c};border-radius:4px;border:2px solid {border};"
            )

    def _accept(self):
        if not self.title_edit.text().strip():
            return
        self.accept()

    def _delete(self):
        self._deleted = True
        self.accept()

    def get_data(self):
        qd = self.date_edit.date()
        all_day = self.all_day_cb.isChecked()
        return {
            "title": self.title_edit.text().strip(),
            "date": date(qd.year(), qd.month(), qd.day()).isoformat(),
            "time": None if all_day else self.start_time.time().toString("HH:mm"),
            "end_time": None if all_day else self.end_time.time().toString("HH:mm"),
            "all_day": all_day,
            "notes": self.notes_edit.toPlainText().strip() or None,
            "color": self._selected_color,
        }

    @property
    def deleted(self):
        return self._deleted
