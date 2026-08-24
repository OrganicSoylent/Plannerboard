from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QDialog, QLineEdit,
    QListWidget, QListWidgetItem, QDialogButtonBox, QToolTip,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib

matplotlib.use("QtAgg")

from plannerboard.services import weather_service as ws
from plannerboard.ui import theme

REFRESH_MS = 30 * 60 * 1000  # 30 minutes


# ── Background workers ─────────────────────────────────────────────────────

class _WeatherFetcher(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, lat, lon, unit, wind_unit):
        super().__init__()
        self.lat, self.lon = lat, lon
        self.unit, self.wind_unit = unit, wind_unit

    def run(self):
        try:
            self.done.emit(ws.get_weather(self.lat, self.lon, self.unit, self.wind_unit))
        except Exception as e:
            self.error.emit(str(e))


class _GeocodeFetcher(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            self.done.emit(ws.geocode(self.query))
        except Exception as e:
            self.error.emit(str(e))


# ── Location search dialog ────────────────────────────────────────────────

class LocationSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Location")
        self.setMinimumWidth(420)
        self._result = None
        self._fetcher = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Enter city name…")
        self._edit.returnPressed.connect(self._search)
        search_row.addWidget(self._edit)
        self._btn = QPushButton("Search")
        self._btn.clicked.connect(self._search)
        search_row.addWidget(self._btn)
        layout.addLayout(search_row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{theme.SUBTEXT};font-size:9pt;")
        layout.addWidget(self._status)

        self._list = QListWidget()
        self._list.setFixedHeight(200)
        self._list.itemDoubleClicked.connect(self._select_item)
        layout.addWidget(self._list)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept_selected)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _search(self):
        q = self._edit.text().strip()
        if not q:
            return
        self._list.clear()
        self._status.setText("Searching…")
        self._btn.setEnabled(False)
        self._fetcher = _GeocodeFetcher(q)
        self._fetcher.done.connect(self._on_results)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()

    def _on_results(self, results):
        self._btn.setEnabled(True)
        self._status.setText(f"{len(results)} result(s)" if results else "No results found")
        for r in results:
            parts = [r["name"]]
            if r.get("admin1"):
                parts.append(r["admin1"])
            parts.append(r.get("country", r.get("country_code", "")))
            item = QListWidgetItem(", ".join(parts))
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def _on_error(self, msg):
        self._btn.setEnabled(True)
        self._status.setText(f"Error: {msg}")

    def _select_item(self, item):
        self._result = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _accept_selected(self):
        cur = self._list.currentItem()
        if cur:
            self._result = cur.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def get_result(self):
        return self._result


# ── Sub-widgets ────────────────────────────────────────────────────────────

class _DayCard(QFrame):
    def __init__(self, day_name, icon, t_max, t_min, unit_sym, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def lbl(text, size=9, color=theme.TEXT, bold=False):
            l = QLabel(text)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setFont(QFont("Sans", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
            l.setStyleSheet(f"color:{color};background:transparent;")
            return l

        layout.addWidget(lbl(day_name, 8, theme.SUBTEXT))
        layout.addWidget(lbl(icon, 13))
        layout.addWidget(lbl(f"{t_max:.0f}°{unit_sym}", 9, theme.TEXT, True))
        layout.addWidget(lbl(f"{t_min:.0f}°{unit_sym}", 8, theme.SUBTEXT))


class _HourlyChart(FigureCanvasQTAgg):
    def __init__(self):
        fig = Figure(figsize=(4, 1.3), tight_layout=True)
        fig.patch.set_facecolor(theme.SURFACE)
        super().__init__(fig)
        self.ax = fig.add_subplot(111)
        self._style()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(110)
        self.setMouseTracking(True)

        # Stored for tooltip lookup
        self._times: list = []
        self._temps: list = []
        self._feels: list = []
        self._precip: list = []
        self._winds: list = []
        self._unit_sym = "C"
        self._wind_unit = "kmh"

        self.mpl_connect("motion_notify_event", self._on_hover)

    def _style(self):
        ax = self.ax
        ax.set_facecolor(theme.SURFACE)
        ax.tick_params(colors=theme.SUBTEXT, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(theme.BORDER)
            spine.set_linewidth(0.5)

    def update_data(self, times, temps, precip_prob, feels, winds, unit_sym, wind_unit):
        self._times = times
        self._temps = temps
        self._feels = feels
        self._precip = precip_prob
        self._winds = winds
        self._unit_sym = unit_sym
        self._wind_unit = wind_unit

        self.ax.clear()
        self._style()
        ax = self.ax

        ax2 = ax.twinx()
        ax2.set_facecolor("none")
        ax2.bar(range(len(precip_prob)), precip_prob, color=theme.BLUE,
                alpha=0.20, width=0.9)
        ax2.set_ylim(0, 100)
        ax2.set_yticks([])
        ax2.spines[:].set_visible(False)

        ax.plot(range(len(temps)), temps, color=theme.BLUE, linewidth=1.8,
                marker="o", markersize=2.5, markerfacecolor=theme.PEACH,
                markeredgewidth=0)
        ax.set_xticks(range(0, len(times), 3))
        ax.set_xticklabels([t[11:16] for t in times[::3]],
                           fontsize=7, color=theme.SUBTEXT)
        ax.set_ylabel(f"°{unit_sym}", fontsize=7, color=theme.SUBTEXT)
        ax.set_xlim(-0.5, len(temps) - 0.5)
        ax.grid(axis="y", color=theme.BORDER, linewidth=0.4, linestyle="--")
        self.draw()

    def _on_hover(self, event):
        if event.inaxes is None or not self._times:
            QToolTip.hideText()
            return
        x = event.xdata
        if x is None:
            QToolTip.hideText()
            return
        idx = max(0, min(round(x), len(self._times) - 1))
        time_str = self._times[idx][11:16]
        temp = self._temps[idx]
        feels = self._feels[idx]
        precip = self._precip[idx]
        wind = self._winds[idx]
        sym = self._unit_sym
        wu = self._wind_unit
        text = (
            f"<b>{time_str}</b><br>"
            f"🌡 {temp:.0f}°{sym}&nbsp;&nbsp;feels {feels:.0f}°{sym}<br>"
            f"🌧 {precip:.0f}%&nbsp;&nbsp;💨 {wind:.0f} {wu}"
        )
        QToolTip.showText(QCursor.pos(), text, self)


# ── Main widget ────────────────────────────────────────────────────────────

class WeatherWidget(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._fetcher = None
        self._lat = config.get("latitude")
        self._lon = config.get("longitude")
        self._city = config.get("city", "—")
        self._unit = config.get("temperature_unit", "celsius")
        self._wind_unit = config.get("wind_speed_unit", "kmh")
        self._unit_sym = "C" if self._unit == "celsius" else "F"
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_MS)

        if self._lat and self._lon:
            self.refresh()

    def _build_ui(self):
        self.setStyleSheet(f"background:{theme.SURFACE};border-radius:8px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(6)

        # ── Header: location + search + refresh ────────────────────────────
        hdr = QHBoxLayout()
        self._city_label = QLabel(f"📍 {self._city}")
        self._city_label.setStyleSheet(
            f"color:{theme.SUBTEXT};font-size:9pt;background:transparent;"
        )
        hdr.addWidget(self._city_label)
        hdr.addStretch()

        self._loc_btn = QPushButton("Loc.")
        self._loc_btn.setFixedSize(60, 26)
        self._loc_btn.setToolTip("Set a different location")
        self._loc_btn.clicked.connect(self._search_location)
        hdr.addWidget(self._loc_btn)

        self._refresh_btn = QPushButton("↺")
        self._refresh_btn.setFixedSize(40, 26)
        self._refresh_btn.setToolTip("Refresh weather")
        self._refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self._refresh_btn)
        root.addLayout(hdr)

        # ── Current conditions: icon badge + details ───────────────────────
        cur = QHBoxLayout()
        cur.setSpacing(12)

        self._icon_frame = QFrame()
        self._icon_frame.setFixedSize(68, 68)
        self._icon_frame.setStyleSheet(
            f"background:{theme.SURFACE2};border-radius:14px;"
        )
        icon_inner = QVBoxLayout(self._icon_frame)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        self._icon_label = QLabel("—")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size:28pt; background:transparent;")
        icon_inner.addWidget(self._icon_label)
        cur.addWidget(self._icon_frame)

        details = QVBoxLayout()
        details.setSpacing(2)
        self._temp_label = QLabel("—")
        self._temp_label.setFont(QFont("Sans", 22, QFont.Weight.Bold))
        self._temp_label.setStyleSheet(f"color:{theme.TEXT};background:transparent;")
        self._desc_label = QLabel("Loading…")
        self._desc_label.setStyleSheet(
            f"color:{theme.SUBTEXT};font-size:10pt;background:transparent;"
        )
        self._feels_label = QLabel("")
        self._feels_label.setStyleSheet(
            f"color:{theme.SUBTEXT};font-size:9pt;background:transparent;"
        )
        self._wind_label = QLabel("")
        self._wind_label.setStyleSheet(
            f"color:{theme.SUBTEXT};font-size:9pt;background:transparent;"
        )
        details.addWidget(self._temp_label)
        details.addWidget(self._desc_label)
        details.addWidget(self._feels_label)
        details.addWidget(self._wind_label)
        details.addStretch()
        cur.addLayout(details)
        cur.addStretch()
        root.addLayout(cur)

        # ── Divider ────────────────────────────────────────────────────────
        root.addWidget(self._divider())

        # ── Hourly chart (hover for details) ──────────────────────────────
        self._chart = _HourlyChart()
        root.addWidget(self._chart)

        # ── Divider ────────────────────────────────────────────────────────
        root.addWidget(self._divider())

        # ── Daily forecast strip ───────────────────────────────────────────
        self._forecast_scroll = QScrollArea()
        self._forecast_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._forecast_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._forecast_scroll.setFixedHeight(90)
        self._forecast_scroll.setWidgetResizable(True)
        self._forecast_scroll.setStyleSheet(
            f"background:{theme.SURFACE};border:none;"
        )
        self._forecast_container = QWidget()
        self._forecast_container.setStyleSheet(f"background:{theme.SURFACE};")
        self._forecast_layout = QHBoxLayout(self._forecast_container)
        self._forecast_layout.setContentsMargins(0, 0, 0, 0)
        self._forecast_layout.setSpacing(4)
        self._forecast_layout.addStretch()
        self._forecast_scroll.setWidget(self._forecast_container)
        root.addWidget(self._forecast_scroll)

        # ── Source attribution ─────────────────────────────────────────────
        root.addWidget(self._divider())
        src_row = QHBoxLayout()
        src_row.addStretch()
        src = QLabel('<a href="https://open-meteo.com" style="color:#6c7086;">Open-Meteo.com</a>')
        src.setOpenExternalLinks(True)
        src.setStyleSheet("font-size:7pt;background:transparent;")
        src_row.addWidget(src)
        root.addLayout(src_row)

        # ── Error label ────────────────────────────────────────────────────
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            f"color:{theme.RED};font-size:8pt;background:transparent;"
        )
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

    def _divider(self):
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{theme.BORDER};background:{theme.BORDER};max-height:1px;")
        return div

    # ── location search ────────────────────────────────────────────────────

    def _search_location(self):
        dlg = LocationSearchDialog(self)
        if dlg.exec() and dlg.get_result():
            r = dlg.get_result()
            city = r["name"]
            country = r.get("country_code", "")
            self.set_location(r["latitude"], r["longitude"], city, country)

    # ── data loading ───────────────────────────────────────────────────────

    def set_location(self, lat, lon, city, country_code=""):
        self._lat = lat
        self._lon = lon
        self._city = f"{city}, {country_code}" if country_code else city
        self._city_label.setText(f"📍 {self._city}")
        self._config.set("latitude", lat)
        self._config.set("longitude", lon)
        self._config.set("city", city)
        self.refresh()

    def refresh(self):
        if not self._lat or not self._lon:
            self._desc_label.setText("No location — click 'Loc.' to set one")
            return
        self._refresh_btn.setEnabled(False)
        self._desc_label.setText("Updating…")
        self._fetcher = _WeatherFetcher(
            self._lat, self._lon, self._unit, self._wind_unit
        )
        self._fetcher.done.connect(self._on_data)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()

    def _on_data(self, data):
        self._refresh_btn.setEnabled(True)
        self._error_label.setText("")
        cur = data["current"]
        sym = self._unit_sym

        code = cur["weathercode"]
        icon = ws.wmo_icon(code)
        bg_color = ws.wmo_bg_color(code)
        temp = cur["temperature_2m"]
        feels = cur["apparent_temperature"]
        desc = ws.wmo_description(code)
        wind = cur["windspeed_10m"]
        hum = cur["relativehumidity_2m"]

        self._icon_label.setText(icon)
        self._icon_frame.setStyleSheet(
            f"background:{bg_color};border-radius:14px;"
        )
        self._temp_label.setText(f"{temp:.0f}°{sym}")
        self._desc_label.setText(desc)
        self._feels_label.setText(f"Feels like {feels:.0f}°{sym}")
        self._wind_label.setText(
            f"💨 {wind:.0f} {self._wind_unit}   💧 {hum}%"
        )

        # Hourly chart (next 24 h from now)
        h = data["hourly"]
        now_str = cur.get("time", "")[:13]
        try:
            start = next(i for i, t in enumerate(h["time"]) if t[:13] >= now_str)
        except StopIteration:
            start = 0
        end = start + 24

        self._chart.update_data(
            h["time"][start:end],
            h["temperature_2m"][start:end],
            h["precipitation_probability"][start:end],
            h.get("apparent_temperature", h["temperature_2m"])[start:end],
            h["windspeed_10m"][start:end],
            sym,
            self._wind_unit,
        )

        # Daily forecast cards
        while self._forecast_layout.count() > 1:
            item = self._forecast_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        d = data["daily"]
        for i in range(min(7, len(d["time"]))):
            dt = datetime.fromisoformat(d["time"][i])
            card = _DayCard(
                dt.strftime("%a"),
                ws.wmo_icon(d["weathercode"][i]),
                d["temperature_2m_max"][i],
                d["temperature_2m_min"][i],
                sym,
            )
            self._forecast_layout.insertWidget(i, card)

    def _on_error(self, msg):
        self._refresh_btn.setEnabled(True)
        self._error_label.setText(f"⚠ {msg}")
