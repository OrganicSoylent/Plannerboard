import calendar
from datetime import date, timedelta

from PyQt6.QtWidgets import QWidget, QScrollArea, QGridLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from plannerboard.ui import theme

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class _MiniMonth(QWidget):
    month_clicked = pyqtSignal(int, int)  # year, month

    CELL = 24
    HDR = 18
    DAY_HDR = 16
    COLS = 7

    def __init__(self, year, month, event_dates, holiday_dates, parent=None):
        super().__init__(parent)
        self._year = year
        self._month = month
        self._event_dates = event_dates
        self._holiday_dates = holiday_dates
        cal = calendar.Calendar(firstweekday=0)
        days = list(cal.itermonthdates(year, month))
        while len(days) < 42:
            days.append(days[-1] + timedelta(1))
        self._grid = [days[i:i+7] for i in range(0, 42, 7)]
        rows = 6
        total_h = self.HDR + self.DAY_HDR + rows * self.CELL + 4
        self.setFixedSize(self.COLS * self.CELL, total_h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        today = date.today()
        cell = self.CELL

        # Month name header
        p.fillRect(0, 0, w, self.HDR, QColor(theme.SURFACE))
        p.setPen(QColor(theme.BLUE if (self._year == today.year and self._month == today.month) else theme.TEXT))
        p.setFont(QFont("Sans", 9, QFont.Weight.Bold))
        p.drawText(QRectF(0, 0, w, self.HDR),
                   Qt.AlignmentFlag.AlignCenter, MONTH_NAMES[self._month - 1])

        # Day-name row
        day_names = ["M", "T", "W", "T", "F", "S", "S"]
        for i, dn in enumerate(day_names):
            col_c = theme.PEACH if i >= 5 else theme.SUBTEXT
            p.setPen(QColor(col_c))
            p.setFont(QFont("Sans", 7))
            p.drawText(QRectF(i * cell, self.HDR, cell, self.DAY_HDR),
                       Qt.AlignmentFlag.AlignCenter, dn)

        # Day cells
        for row, week in enumerate(self._grid):
            for col, d in enumerate(week):
                x = col * cell
                y = self.HDR + self.DAY_HDR + row * cell
                is_today = d == today
                in_month = d.month == self._month

                if is_today:
                    bg = QColor(theme.BLUE)
                    p.fillRect(QRectF(x + 2, y + 2, cell - 4, cell - 4), bg)

                p.setPen(QColor(theme.TEXT if in_month else theme.OVERLAY))
                p.setFont(QFont("Sans", 7, QFont.Weight.Bold if is_today else QFont.Weight.Normal))
                txt_color = theme.BG if is_today else (theme.TEXT if in_month else theme.OVERLAY)
                p.setPen(QColor(txt_color))
                p.drawText(QRectF(x, y, cell, cell),
                           Qt.AlignmentFlag.AlignCenter, str(d.day))

                # Dot for event
                if in_month and d in self._event_dates:
                    dot_clr = QColor(theme.BG if is_today else theme.BLUE)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(dot_clr)
                    p.drawEllipse(QRectF(x + cell / 2 - 2, y + cell - 5, 4, 4))
                    p.setBrush(Qt.BrushStyle.NoBrush)

                # Holiday marker
                if in_month and d in self._holiday_dates:
                    hl = QColor(theme.YELLOW)
                    hl.setAlpha(120)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(hl)
                    p.drawRect(QRectF(x + 1, y + 1, cell - 2, cell - 2))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QColor(txt_color))
                    p.setFont(QFont("Sans", 7))
                    p.drawText(QRectF(x, y, cell, cell),
                               Qt.AlignmentFlag.AlignCenter, str(d.day))

        p.setPen(QPen(QColor(theme.BORDER), 0.5))
        p.drawRect(0, 0, w - 1, self.height() - 1)

    def mousePressEvent(self, _):
        self.month_clicked.emit(self._year, self._month)


class YearView(QScrollArea):
    month_double_clicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._container = QWidget()
        self._layout = QGridLayout(self._container)
        self._layout.setSpacing(16)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self.setWidget(self._container)
        self._year = date.today().year
        self._events = []
        self._holidays = {}

    def set_period(self, year, events, holidays):
        self._year = year
        self._events = events
        self._holidays = holidays
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        event_dates = {date.fromisoformat(e["date"]) for e in self._events}
        holiday_dates = set(self._holidays.keys())

        for m in range(1, 13):
            row, col = divmod(m - 1, 4)
            mini = _MiniMonth(self._year, m, event_dates, holiday_dates)
            mini.month_clicked.connect(self.month_double_clicked)
            self._layout.addWidget(mini, row, col, Qt.AlignmentFlag.AlignCenter)
