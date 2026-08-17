from datetime import date, timedelta

from PyQt6.QtWidgets import QWidget, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from plannerboard.ui import theme

HOUR_H = 60
HEADER_H = 44
TIME_W = 60
START_HOUR = 0
END_HOUR = 24
TOTAL_H = HOUR_H * (END_HOUR - START_HOUR) + HEADER_H


class _DayCanvas(QWidget):
    slot_double_clicked = pyqtSignal(date, int)
    event_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date = date.today()
        self._events: list[dict] = []
        self._holidays: dict = {}
        self.setFixedHeight(TOTAL_H)
        self.setMouseTracking(True)
        self._hover_hour: int | None = None

    def set_day(self, d: date, events, holidays):
        self._date = d
        self._events = events
        self._holidays = holidays
        self.update()

    def _hour_y(self, hour):
        return HEADER_H + (hour - START_HOUR) * HOUR_H

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p)

    def _draw(self, p):
        w = self.width()
        today = date.today()

        p.fillRect(0, 0, w, TOTAL_H, QColor(theme.BG))

        # Header
        is_today = self._date == today
        hdr_bg = QColor(theme.BLUE) if is_today else QColor(theme.SURFACE)
        p.fillRect(0, 0, w, HEADER_H, hdr_bg)
        p.setPen(QColor(theme.BG if is_today else theme.TEXT))
        p.setFont(QFont("Sans", 13, QFont.Weight.Bold))
        label = self._date.strftime("%A, %-d %B %Y")
        hol = self._holidays.get(self._date)
        if hol:
            label += f"  ·  {hol}"
        p.drawText(QRectF(TIME_W, 0, w - TIME_W, HEADER_H),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

        # All-day events strip
        all_day = [e for e in self._events if e.get("all_day")]
        ad_y = 2
        for ev in all_day[:3]:
            clr = QColor(ev.get("color", theme.BLUE))
            p.fillRect(QRectF(TIME_W + 4, ad_y, w - TIME_W - 8, 12), clr)
            p.setPen(QColor(theme.BG))
            p.setFont(QFont("Sans", 8))
            p.drawText(QRectF(TIME_W + 6, ad_y, w - TIME_W - 12, 12),
                       Qt.AlignmentFlag.AlignVCenter, ev["title"])
            ad_y += 13

        # Hour grid
        for hour in range(START_HOUR, END_HOUR + 1):
            y = self._hour_y(hour)
            if hour < END_HOUR:
                p.setPen(QColor(theme.SUBTEXT))
                p.setFont(QFont("Sans", 9))
                p.drawText(QRectF(0, y + 2, TIME_W - 6, 18),
                           Qt.AlignmentFlag.AlignRight, f"{hour:02d}:00")
            p.setPen(QPen(QColor(theme.BORDER), 0.5))
            p.drawLine(QPointF(TIME_W, y), QPointF(w, y))
            if hour < END_HOUR:
                yh = y + HOUR_H / 2
                p.setPen(QPen(QColor(theme.SURFACE2), 0.5))
                p.drawLine(QPointF(TIME_W, yh), QPointF(w, yh))

        # Hover
        if self._hover_hour is not None:
            y = self._hour_y(self._hover_hour)
            hov = QColor(theme.BLUE)
            hov.setAlpha(20)
            p.fillRect(QRectF(TIME_W, y, w - TIME_W, HOUR_H), hov)

        # Timed events
        timed = [e for e in self._events if not e.get("all_day") and e.get("time")]
        for ev in timed:
            tp = [int(x) for x in ev["time"].split(":")]
            hour_frac = tp[0] + tp[1] / 60 - START_HOUR
            ey = HEADER_H + hour_frac * HOUR_H
            duration = 1.0
            if ev.get("end_time"):
                ep = [int(x) for x in ev["end_time"].split(":")]
                duration = (ep[0] + ep[1] / 60) - (tp[0] + tp[1] / 60)
            eh = max(HOUR_H * duration - 2, 20)
            clr = QColor(ev.get("color", theme.BLUE))
            p.fillRect(QRectF(TIME_W + 4, ey, w - TIME_W - 8, eh), clr)
            p.setPen(QColor(theme.BG))
            p.setFont(QFont("Sans", 9, QFont.Weight.Bold))
            p.drawText(QRectF(TIME_W + 8, ey + 2, w - TIME_W - 16, min(eh, 18)),
                       Qt.AlignmentFlag.AlignVCenter, ev["title"])
            if ev.get("notes") and eh > 30:
                p.setFont(QFont("Sans", 8))
                p.drawText(QRectF(TIME_W + 8, ey + 18, w - TIME_W - 16, eh - 20),
                           Qt.AlignmentFlag.AlignTop, ev["notes"])

    def _hour_at(self, pos):
        y = pos.y()
        if y < HEADER_H:
            return None
        h = int((y - HEADER_H) / HOUR_H) + START_HOUR
        return h if START_HOUR <= h < END_HOUR else None

    def mouseMoveEvent(self, ev):
        h = self._hour_at(ev.position())
        if h != self._hover_hour:
            self._hover_hour = h
            self.update()

    def leaveEvent(self, _):
        self._hover_hour = None
        self.update()

    def mouseDoubleClickEvent(self, ev):
        h = self._hour_at(ev.position())
        if h is not None:
            self.slot_double_clicked.emit(self._date, h)


class DayView(QScrollArea):
    slot_double_clicked = pyqtSignal(date, int)
    event_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._canvas = _DayCanvas()
        self.setWidget(self._canvas)
        self._canvas.slot_double_clicked.connect(self.slot_double_clicked)
        self._canvas.event_double_clicked.connect(self.event_double_clicked)

    def set_day(self, d, events, holidays):
        self._canvas.set_day(d, events, holidays)

    def scroll_to_hour(self, hour=8):
        y = max(0, self._canvas._hour_y(hour) - 40)
        self.verticalScrollBar().setValue(y)
