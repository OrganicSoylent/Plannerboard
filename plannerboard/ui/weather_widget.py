from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib

matplotlib.use("QtAgg")

from plannerboard.services import weather_service as ws
from plannerboard.ui import theme

REFRESH_MS = 30 * 60 * 1000  # 30 minutes


class _WeatherFetcher(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, lat, lon, unit, wind_unit):
        super().__init__()
        self.lat, self.lon = lat, lon
        self.unit, self.wind_unit = unit, wind_unit

    def run(self):
        try:
            data = ws.get_weather(self.lat, self.lon, self.unit, self.wind_unit)
            self.done.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class _DayCard(QFrame):
    def __init__(self, day_name, icon, t_max, t_min, unit_sym, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedWidth(54)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def lbl(text, size=9, color=theme.TEXT, bold=False):
            l = QLabel(text)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            f = QFont("Sans", size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
            l.setFont(f)
            l.setStyleSheet(f"color:{color};")
            return l

        layout.addWidget(lbl(day_name, 8, theme.SUBTEXT))
        layout.addWidget(lbl(icon, 14))
        layout.addWidget(lbl(f"{t_max:.0f}°{unit_sym}", 9, theme.TEXT, True))
        layout.addWidget(lbl(f"{t_min:.0f}°{unit_sym}", 8, theme.SUBTEXT))


class _HourlyChart(FigureCanvasQTAgg):
    def __init__(self):
        fig = Figure(figsize=(4, 1.4), tight_layout=True)
        fig.patch.set_facecolor(theme.SURFACE)
        super().__init__(fig)
        self.ax = fig.add_subplot(111)
        self._style_axes()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(120)

    def _style_axes(self):
        ax = self.ax
        ax.set_facecolor(theme.SURFACE)
        ax.tick_params(colors=theme.SUBTEXT, labelsize=7)
        ax.spines[:].set_color(theme.BORDER)
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

    def update_data(self, times, temps, precip_prob, unit_sym):
        self.ax.clear()
        self._style_axes()
        ax = self.ax

        # Precipitation probability bars (background)
        ax2 = ax.twinx()
        ax2.set_facecolor("none")
        ax2.bar(range(len(precip_prob)), precip_prob, color=theme.BLUE,
                alpha=0.18, width=0.9)
        ax2.set_ylim(0, 100)
        ax2.set_yticks([])
        ax2.spines[:].set_visible(False)

        # Temperature line
        ax.plot(range(len(temps)), temps, color=theme.BLUE, linewidth=1.8,
                marker="o", markersize=2.5, markerfacecolor=theme.PEACH,
                markeredgewidth=0)
        ax.set_xticks(range(0, len(times), 3))
        ax.set_xticklabels([t[11:16] for t in times[::3]], fontsize=7,
                           color=theme.SUBTEXT)
        ax.set_ylabel(f"°{unit_sym}", fontsize=7, color=theme.SUBTEXT)
        ax.yaxis.label.set_color(theme.SUBTEXT)
        ax.set_xlim(-0.5, len(temps) - 0.5)
        ax.grid(axis="y", color=theme.BORDER, linewidth=0.4, linestyle="--")
        self.draw()


class WeatherWidget(QWidget):
    radar_toggled = pyqtSignal()

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

    # ── build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"background:{theme.SURFACE};border-radius:8px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # Header row: city + refresh button
        hdr = QHBoxLayout()
        self._city_label = QLabel(f"📍 {self._city}")
        self._city_label.setStyleSheet(f"color:{theme.SUBTEXT};font-size:9pt;")
        hdr.addWidget(self._city_label)
        hdr.addStretch()
        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setFixedSize(26, 26)
        self._refresh_btn.setToolTip("Refresh weather")
        self._refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self._refresh_btn)
        root.addLayout(hdr)

        # Current conditions
        cur = QHBoxLayout()
        self._icon_temp = QLabel("—")
        self._icon_temp.setFont(QFont("Sans", 28, QFont.Weight.Bold))
        self._icon_temp.setStyleSheet(f"color:{theme.TEXT};")
        cur.addWidget(self._icon_temp)
        cur.addSpacing(8)

        details = QVBoxLayout()
        details.setSpacing(2)
        self._desc_label = QLabel("Loading…")
        self._desc_label.setStyleSheet(f"color:{theme.SUBTEXT};font-size:10pt;")
        self._feels_label = QLabel("")
        self._feels_label.setStyleSheet(f"color:{theme.SUBTEXT};font-size:9pt;")
        self._wind_label = QLabel("")
        self._wind_label.setStyleSheet(f"color:{theme.SUBTEXT};font-size:9pt;")
        details.addWidget(self._desc_label)
        details.addWidget(self._feels_label)
        details.addWidget(self._wind_label)
        details.addStretch()
        cur.addLayout(details)
        cur.addStretch()
        root.addLayout(cur)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{theme.BORDER};")
        root.addWidget(div)

        # Hourly chart
        self._chart = _HourlyChart()
        root.addWidget(self._chart)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet(f"color:{theme.BORDER};")
        root.addWidget(div2)

        # Daily forecast strip
        self._forecast_scroll = QScrollArea()
        self._forecast_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._forecast_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._forecast_scroll.setFixedHeight(88)
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

        # Radar toggle button
        self._radar_btn = QPushButton("🗺  Radar  ▼")
        self._radar_btn.setFixedHeight(28)
        self._radar_btn.clicked.connect(self.radar_toggled)
        root.addWidget(self._radar_btn)

        # Error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color:{theme.RED};font-size:8pt;")
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

    # ── data loading ──────────────────────────────────────────────────────

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
            self._desc_label.setText("No location set")
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

        icon = ws.wmo_icon(cur["weathercode"])
        temp = cur["temperature_2m"]
        feels = cur["apparent_temperature"]
        desc = ws.wmo_description(cur["weathercode"])
        wind = cur["windspeed_10m"]
        hum = cur["relativehumidity_2m"]

        self._icon_temp.setText(f"{icon}  {temp:.0f}°{sym}")
        self._desc_label.setText(desc)
        self._feels_label.setText(f"Feels like {feels:.0f}°{sym}")
        self._wind_label.setText(f"💨 {wind:.0f} {self._wind_unit}   💧 {hum}%")

        # Hourly chart (next 24h)
        h = data["hourly"]
        now_str = cur.get("time", "")[:13]
        try:
            start = next(
                i for i, t in enumerate(h["time"]) if t[:13] >= now_str
            )
        except StopIteration:
            start = 0
        end = start + 24
        self._chart.update_data(
            h["time"][start:end],
            h["temperature_2m"][start:end],
            h["precipitation_probability"][start:end],
            sym,
        )

        # Daily forecast
        while self._forecast_layout.count() > 1:
            item = self._forecast_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        d = data["daily"]
        days_to_show = min(7, len(d["time"]))
        for i in range(days_to_show):
            dt = datetime.fromisoformat(d["time"][i])
            day_name = dt.strftime("%a")
            icon_d = ws.wmo_icon(d["weathercode"][i])
            t_max = d["temperature_2m_max"][i]
            t_min = d["temperature_2m_min"][i]
            card = _DayCard(day_name, icon_d, t_max, t_min, sym)
            self._forecast_layout.insertWidget(i, card)

    def _on_error(self, msg):
        self._refresh_btn.setEnabled(True)
        self._error_label.setText(f"⚠ {msg}")

    def set_radar_open(self, is_open: bool):
        self._radar_btn.setText("🗺  Radar  ▲" if is_open else "🗺  Radar  ▼")
