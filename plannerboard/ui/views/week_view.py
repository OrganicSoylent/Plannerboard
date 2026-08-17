from datetime import date, timedelta, time as dtime

from PyQt6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics

from plannerboard.ui import theme

HOUR_H = 56          # pixels per hour
HEADER_H = 40
TIME_W = 52
START_HOUR = 0
END_HOUR = 24
TOTAL_H = HOUR_H * (END_HOUR - START_HOUR) + HEADER_H


class _WeekCanvas(QWidget):
    slot_double_clicked = pyqtSignal(date, int)
    event_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._week_start = date.today() - timedelta(days=date.today().weekday())
        self._events: list[dict] = []
        self._holidays: dict = {}
        self.setFixedHeight(TOTAL_H)
        self.setMouseTracking(True)
        self._hover_slot: tuple | None = None

    def set_week(self, week_start: date, events, holidays):
        self._week_start = week_start
        self._events = events
        self._holidays = holidays
        self.update()

    def _days(self):
        return [self._week_start + timedelta(i) for i in range(7)]

    def _col_x(self, col, w):
        day_w = (w - TIME_W) / 7
        return TIME_W + col * day_w

    def _col_w(self, w):
        return (w - TIME_W) / 7

    def _hour_y(self, hour):
        return HEADER_H + (hour - START_HOUR) * HOUR_H

    # ── painting ──────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p)

    def _draw(self, p):
        w = self.width()
        today = date.today()
        days = self._days()
        col_w = self._col_w(w)

        # Background
        p.fillRect(0, 0, w, TOTAL_H, QColor(theme.BG))

        # Day headers
        for i, d in enumerate(days):
            x = self._col_x(i, w)
            is_today = d == today
            is_wknd = i >= 5
            bg = QColor(theme.BLUE) if is_today else (
                QColor(theme.SURFACE2) if is_wknd else QColor(theme.SURFACE)
            )
            p.fillRect(QRectF(x, 0, col_w, HEADER_H), bg)
            txt_c = theme.BG if is_today else theme.TEXT
            p.setPen(QColor(txt_c))
            p.setFont(QFont("Sans", 9, QFont.Weight.Bold if is_today else QFont.Weight.Normal))
            label = d.strftime("%a %-d")
            hol = self._holidays.get(d)
            if hol:
                label += f"\n{hol[:12]}"
            p.drawText(QRectF(x, 0, col_w, HEADER_H),
                       Qt.AlignmentFlag.AlignCenter, label)

        # Hour rows
        for hour in range(START_HOUR, END_HOUR + 1):
            y = self._hour_y(hour)
            # Time label
            if hour < END_HOUR:
                p.setPen(QColor(theme.SUBTEXT))
                p.setFont(QFont("Sans", 8))
                p.drawText(QRectF(0, y + 2, TIME_W - 4, 16),
                           Qt.AlignmentFlag.AlignRight, f"{hour:02d}:00")
            # Hour line
            p.setPen(QPen(QColor(theme.BORDER), 0.5))
            p.drawLine(QPointF(TIME_W, y), QPointF(w, y))
            # Half-hour line
            if hour < END_HOUR:
                yh = y + HOUR_H / 2
                p.setPen(QPen(QColor(theme.SURFACE2), 0.5))
                p.drawLine(QPointF(TIME_W, yh), QPointF(w, yh))

        # Column separators
        p.setPen(QPen(QColor(theme.BORDER), 0.5))
        for i in range(8):
            x = self._col_x(i, w) if i < 7 else w
            p.drawLine(QPointF(x, 0), QPointF(x, TOTAL_H))

        # Events
        ev_by_date: dict[str, list] = {}
        for e in self._events:
            ev_by_date.setdefault(e["date"], []).append(e)

        for i, d in enumerate(days):
            x = self._col_x(i, w) + 2
            cw = col_w - 4
            day_evts = ev_by_date.get(d.isoformat(), [])
            all_day = [e for e in day_evts if e.get("all_day")]
            timed = [e for e in day_evts if not e.get("all_day") and e.get("time")]

            # All-day events in header
            for j, ev in enumerate(all_day[:2]):
                ey = 4 + j * 14
                clr = QColor(ev.get("color", theme.BLUE))
                p.fillRect(QRectF(x, ey, cw, 13), clr)
                p.setPen(QColor(theme.BG))
                p.setFont(QFont("Sans", 8))
                p.drawText(QRectF(x + 2, ey, cw - 4, 13),
                           Qt.AlignmentFlag.AlignVCenter, ev["title"])

            # Timed events as blocks
            for ev in timed:
                t_parts = [int(x) for x in ev["time"].split(":")]
                hour = t_parts[0] + t_parts[1] / 60 - START_HOUR
                ey = HEADER_H + hour * HOUR_H
                duration = 1.0
                if ev.get("end_time"):
                    ep = [int(x) for x in ev["end_time"].split(":")]
                    duration = (ep[0] + ep[1] / 60) - (t_parts[0] + t_parts[1] / 60)
                eh = max(HOUR_H * duration - 2, 14)
                clr = QColor(ev.get("color", theme.BLUE))
                p.fillRect(QRectF(x, ey, cw, eh), clr)
                p.setPen(QColor(theme.BG))
                p.setFont(QFont("Sans", 8, QFont.Weight.Bold))
                p.drawText(QRectF(x + 2, ey + 1, cw - 4, min(eh, 16)),
                           Qt.AlignmentFlag.AlignVCenter, ev["title"])

        # Hover highlight
        if self._hover_slot:
            col, hour = self._hover_slot
            x = self._col_x(col, w)
            y = self._hour_y(hour)
            hov = QColor(theme.BLUE)
            hov.setAlpha(20)
            p.fillRect(QRectF(x, y, col_w, HOUR_H), hov)

    # ── mouse ─────────────────────────────────────────────────────────────

    def _slot_at(self, pos):
        w = self.width()
        col_w = self._col_w(w)
        x, y = pos.x(), pos.y()
        if x < TIME_W or y < HEADER_H:
            return None
        col = int((x - TIME_W) / col_w)
        hour = int((y - HEADER_H) / HOUR_H) + START_HOUR
        if 0 <= col <= 6 and START_HOUR <= hour < END_HOUR:
            return col, hour
        return None

    def mouseMoveEvent(self, ev):
        slot = self._slot_at(ev.position())
        if slot != self._hover_slot:
            self._hover_slot = slot
            self.update()

    def leaveEvent(self, _):
        self._hover_slot = None
        self.update()

    def mouseDoubleClickEvent(self, ev):
        slot = self._slot_at(ev.position())
        if slot:
            col, hour = slot
            d = self._days()[col]
            self.slot_double_clicked.emit(d, hour)


class WeekView(QScrollArea):
    slot_double_clicked = pyqtSignal(date, int)
    event_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._canvas = _WeekCanvas()
        self.setWidget(self._canvas)
        self._canvas.slot_double_clicked.connect(self.slot_double_clicked)
        self._canvas.event_double_clicked.connect(self.event_double_clicked)

    def set_week(self, week_start, events, holidays):
        self._canvas.set_week(week_start, events, holidays)

    def scroll_to_hour(self, hour=8):
        y = max(0, self._canvas._hour_y(hour) - 40)
        self.verticalScrollBar().setValue(y)
