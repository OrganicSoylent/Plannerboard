import calendar
from datetime import date, timedelta

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath

from plannerboard.ui import theme

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HEADER_H = 28
MULTI_H = 14      # height of each multi-day bar
MULTI_STEP = 15   # vertical step between stacked bars
DAY_NUM_H = 20    # space for the day number
HOL_H = 13        # space for holiday name
EV_H = 14         # height of single-day event label
EV_STEP = 15      # step between stacked single-day events


def _month_grid(year, month):
    cal = calendar.Calendar(firstweekday=0)
    days = list(cal.itermonthdates(year, month))
    while len(days) < 42:
        days.append(days[-1] + timedelta(1))
    return [days[i:i+7] for i in range(0, 42, 7)]


class MonthView(QWidget):
    date_double_clicked = pyqtSignal(object)   # date
    event_double_clicked = pyqtSignal(dict)    # event dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._year = date.today().year
        self._month = date.today().month
        self._events: list[dict] = []
        self._holidays: dict = {}
        self._grid = _month_grid(self._year, self._month)
        self._hover: date | None = None
        # Populated during paint for hit-testing
        self._event_rects: list[tuple[QRectF, dict]] = []
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
        self._event_rects = []
        self._draw(p)

    def _draw(self, p):
        w = self.width()
        h = self.height()
        cell_w = w / 7
        cell_h = (h - HEADER_H) / 6
        today = date.today()

        # ── Day-name header ────────────────────────────────────────────────
        p.fillRect(0, 0, w, HEADER_H, QColor(theme.SURFACE))
        for i, name in enumerate(DAY_NAMES):
            color = theme.PEACH if i >= 5 else theme.SUBTEXT
            p.setPen(QColor(color))
            p.setFont(QFont("Sans", 9, QFont.Weight.Bold))
            p.drawText(QRectF(i * cell_w, 0, cell_w, HEADER_H),
                       Qt.AlignmentFlag.AlignCenter, name)

        # ── Index events by date string ────────────────────────────────────
        ev_by_date: dict[str, list] = {}
        for e in self._events:
            ev_by_date.setdefault(e["date"], []).append(e)

        # Separate multi-day from single-day events
        multi_events = [e for e in self._events
                        if e.get("end_date") and e["end_date"] != e["date"]]

        # ── Cell backgrounds + day numbers ─────────────────────────────────
        for row, week in enumerate(self._grid):
            for col, d in enumerate(week):
                x = col * cell_w
                y = HEADER_H + row * cell_h
                in_month = d.month == self._month
                is_today = d == today
                is_hover = d == self._hover
                is_weekend = col >= 5

                if is_today:
                    bg = QColor(theme.BLUE); bg.setAlpha(30)
                elif is_hover:
                    bg = QColor(theme.SURFACE2)
                elif not in_month:
                    bg = QColor(theme.BG)
                elif is_weekend:
                    bg = QColor(theme.SURFACE); bg.setAlpha(80)
                else:
                    bg = QColor(theme.SURFACE)

                p.fillRect(QRectF(x, y, cell_w, cell_h), bg)
                p.setPen(QPen(QColor(theme.BORDER), 0.5))
                p.drawRect(QRectF(x, y, cell_w, cell_h))

                # Day number
                num_color = (theme.BLUE if is_today
                             else theme.TEXT if in_month else theme.OVERLAY)
                p.setPen(QColor(num_color))
                p.setFont(QFont("Sans", 10,
                                QFont.Weight.Bold if is_today else QFont.Weight.Normal))
                p.drawText(QRectF(x + 4, y + 2, 28, DAY_NUM_H),
                           Qt.AlignmentFlag.AlignLeft, str(d.day))

        # ── Multi-day event bars (drawn row by row across full cell spans) ──
        row_multi_count = [0] * 6  # how many slots used per row

        for evt in multi_events:
            start_d = date.fromisoformat(evt["date"])
            end_d = date.fromisoformat(evt["end_date"])

            for row, week in enumerate(self._grid):
                if start_d > week[-1] or end_d < week[0]:
                    continue
                slot = row_multi_count[row]
                if slot >= 2:
                    continue
                row_multi_count[row] += 1

                col_start = max(0, (start_d - week[0]).days)
                col_end = min(6, (end_d - week[0]).days)

                y_row = HEADER_H + row * (self.height() - HEADER_H) / 6
                bar_y = y_row + DAY_NUM_H + 2 + slot * MULTI_STEP
                bar_x = col_start * (self.width() / 7) + 3
                bar_w = (col_end - col_start + 1) * (self.width() / 7) - 6

                clr = QColor(evt.get("color", theme.BLUE))
                path = QPainterPath()
                path.addRoundedRect(QRectF(bar_x, bar_y, bar_w, MULTI_H), 5, 5)
                p.fillPath(path, clr)

                # Title on the bar
                p.setPen(QColor(theme.BG))
                p.setFont(QFont("Sans", 8, QFont.Weight.Bold))
                p.drawText(QRectF(bar_x + 6, bar_y, bar_w - 12, MULTI_H),
                           Qt.AlignmentFlag.AlignVCenter, evt["title"])

                self._event_rects.append((QRectF(bar_x, bar_y, bar_w, MULTI_H), evt))

        # ── Single-day events ──────────────────────────────────────────────
        cell_h_actual = (self.height() - HEADER_H) / 6

        for row, week in enumerate(self._grid):
            multi_slots_used = row_multi_count[row]
            ev_top_offset = DAY_NUM_H + 2 + multi_slots_used * MULTI_STEP

            for col, d in enumerate(week):
                x = col * (self.width() / 7)
                y = HEADER_H + row * cell_h_actual
                in_month = d.month == self._month
                cur_y = y + ev_top_offset

                # Holiday name
                if d in self._holidays:
                    p.setPen(QColor(theme.YELLOW))
                    p.setFont(QFont("Sans", 7))
                    p.drawText(QRectF(x + 3, cur_y, self.width() / 7 - 6, HOL_H),
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                               self._holidays[d])
                    cur_y += HOL_H

                # Events for this date (single-day only)
                day_evts = [e for e in ev_by_date.get(d.isoformat(), [])
                            if not (e.get("end_date") and e["end_date"] != e["date"])]
                max_slots = max(0, int((y + cell_h_actual - cur_y - 4) / EV_STEP))
                visible = day_evts[:max_slots]
                overflow = len(day_evts) - len(visible)
                if overflow > 0 and max_slots > 0:
                    visible = day_evts[:max(0, max_slots - 1)]
                    overflow = len(day_evts) - len(visible)

                cw = self.width() / 7
                for i, ev in enumerate(visible):
                    ey = cur_y + i * EV_STEP
                    ev_rect = QRectF(x + 2, ey, cw - 4, EV_H - 2)
                    clr = QColor(ev.get("color", theme.BLUE))
                    clr.setAlpha(220)
                    p.fillRect(ev_rect, clr)
                    p.setPen(QColor(theme.BG))
                    p.setFont(QFont("Sans", 8))
                    p.drawText(ev_rect.adjusted(2, 0, -2, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               ev["title"])
                    self._event_rects.append((ev_rect, ev))

                if overflow > 0:
                    ey = cur_y + len(visible) * EV_STEP
                    p.setPen(QColor(theme.SUBTEXT))
                    p.setFont(QFont("Sans", 8))
                    p.drawText(QRectF(x + 4, ey, cw - 8, EV_H),
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

    def _event_at(self, pos):
        for rect, ev in self._event_rects:
            if rect.contains(pos.x(), pos.y()):
                return ev
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
        pos = ev.position()
        hit = self._event_at(pos)
        if hit:
            self.event_double_clicked.emit(hit)
        else:
            d = self._cell_date(pos)
            if d:
                self.date_double_clicked.emit(d)
