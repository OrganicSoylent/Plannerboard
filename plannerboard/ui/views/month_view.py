import calendar
from datetime import date, timedelta

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from plannerboard.ui import theme

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HEADER_H = 28


def _month_grid(year, month):
    cal = calendar.Calendar(firstweekday=0)
    days = list(cal.itermonthdates(year, month))
    while len(days) < 42:
        days.append(days[-1] + timedelta(1))
    return [days[i:i+7] for i in range(0, 42, 7)]


class MonthView(QWidget):
    date_double_clicked = pyqtSignal(object)
    event_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._year = date.today().year
        self._month = date.today().month
        self._events = []
        self._holidays = {}
        self._grid = _month_grid(self._year, self._month)
        self._hover = None
        self.setMouseTracking(True)
        self.setMinimumHeight(400)

    def set_period(self, year, month, events, holidays):
        self._year = year
        self._month = month
        self._events = events
        self._holidays = holidays
        self._grid = _month_grid(year, month)
        self.update()

    # ── painting ──────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p)

    def _draw(self, p):
        w = self.width()
        h = self.height()
        cell_w = w / 7
        cell_h = (h - HEADER_H) / 6
        today = date.today()

        # Day-name header
        p.fillRect(0, 0, w, HEADER_H, QColor(theme.SURFACE))
        for i, name in enumerate(DAY_NAMES):
            color = theme.SUBTEXT if i < 5 else theme.PEACH
            p.setPen(QColor(color))
            p.setFont(QFont("Sans", 9, QFont.Weight.Bold))
            p.drawText(
                QRectF(i * cell_w, 0, cell_w, HEADER_H),
                Qt.AlignmentFlag.AlignCenter, name
            )

        # Event index keyed by date string
        ev_by_date: dict[str, list] = {}
        for e in self._events:
            ev_by_date.setdefault(e["date"], []).append(e)

        for row, week in enumerate(self._grid):
            for col, d in enumerate(week):
                x = col * cell_w
                y = HEADER_H + row * cell_h

                # Background
                is_today = d == today
                in_month = d.month == self._month
                is_weekend = col >= 5
                is_hover = d == self._hover

                if is_today:
                    bg = QColor(theme.BLUE)
                    bg.setAlpha(30)
                elif is_hover:
                    bg = QColor(theme.SURFACE2)
                elif not in_month:
                    bg = QColor(theme.BG)
                elif is_weekend:
                    bg = QColor(theme.SURFACE)
                    bg.setAlpha(80)
                else:
                    bg = QColor(theme.SURFACE)

                p.fillRect(QRectF(x, y, cell_w, cell_h), bg)

                # Grid border
                p.setPen(QPen(QColor(theme.BORDER), 0.5))
                p.drawRect(QRectF(x, y, cell_w, cell_h))

                # Day number
                num_color = theme.BLUE if is_today else (theme.TEXT if in_month else theme.OVERLAY)
                p.setPen(QColor(num_color))
                p.setFont(QFont("Sans", 10, QFont.Weight.Bold if is_today else QFont.Weight.Normal))
                p.drawText(QRectF(x + 4, y + 2, 28, 18), Qt.AlignmentFlag.AlignLeft, str(d.day))

                # Holiday
                hol_y = y + 20
                if d in self._holidays:
                    p.setPen(QColor(theme.YELLOW))
                    p.setFont(QFont("Sans", 7))
                    hname = self._holidays[d]
                    p.drawText(QRectF(x + 3, hol_y, cell_w - 6, 13),
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                               hname)
                    hol_y += 13

                # Events (max 3 slots visible)
                evts = ev_by_date.get(d.isoformat(), [])
                ev_slot_h = 14
                max_slots = max(0, int((cell_h - (hol_y - y) - 4) / ev_slot_h))
                visible = evts[:max_slots]
                overflow = len(evts) - len(visible)
                if overflow > 0:
                    visible = evts[:max(0, max_slots - 1)]
                    overflow = len(evts) - len(visible)

                for i, ev in enumerate(visible):
                    ey = hol_y + i * ev_slot_h
                    clr = QColor(ev.get("color", theme.BLUE))
                    clr.setAlpha(220)
                    p.fillRect(QRectF(x + 2, ey, cell_w - 4, ev_slot_h - 2), clr)
                    p.setPen(QColor(theme.BG))
                    p.setFont(QFont("Sans", 8))
                    p.drawText(QRectF(x + 4, ey, cell_w - 8, ev_slot_h - 2),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               ev["title"])

                if overflow > 0:
                    ey = hol_y + len(visible) * ev_slot_h
                    p.setPen(QColor(theme.SUBTEXT))
                    p.setFont(QFont("Sans", 8))
                    p.drawText(QRectF(x + 4, ey, cell_w - 8, ev_slot_h),
                               Qt.AlignmentFlag.AlignVCenter,
                               f"+{overflow} more")

    # ── mouse ─────────────────────────────────────────────────────────────

    def _cell_date(self, pos):
        w = self.width()
        h = self.height()
        cell_w = w / 7
        cell_h = (h - HEADER_H) / 6
        x, y = pos.x(), pos.y()
        if y < HEADER_H:
            return None
        col = int(x / cell_w)
        row = int((y - HEADER_H) / cell_h)
        if 0 <= col <= 6 and 0 <= row <= 5:
            return self._grid[row][col]
        return None

    def mouseMoveEvent(self, ev):
        d = self._cell_date(ev.position())
        if d != self._hover:
            self._hover = d
            self.update()

    def leaveEvent(self, _):
        self._hover = None
        self.update()

    def mouseDoubleClickEvent(self, ev):
        d = self._cell_date(ev.position())
        if d:
            self.date_double_clicked.emit(d)
