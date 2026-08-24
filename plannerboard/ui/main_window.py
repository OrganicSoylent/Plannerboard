from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from plannerboard.ui.calendar_widget import CalendarWidget
from plannerboard.ui.weather_widget import WeatherWidget
from plannerboard.ui.settings_dialog import SettingsDialog
from plannerboard.ui import theme
from plannerboard.services.location_service import get_location


class _LocationFetcher(QThread):
    done = pyqtSignal(dict)

    def run(self):
        loc = get_location()
        if loc:
            self.done.emit(loc)


class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self._config = config
        self.setWindowTitle("Plannerboard")
        self._restore_geometry()
        self._build_ui()
        self._build_menu()
        self._auto_locate()

    # ── geometry ──────────────────────────────────────────────────────────

    def _restore_geometry(self):
        w = self._config.get("window_width", 1400)
        h = self._config.get("window_height", 900)
        x = self._config.get("window_x")
        y = self._config.get("window_y")
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)

    def closeEvent(self, ev):
        geo = self.geometry()
        self._config.set("window_x", geo.x())
        self._config.set("window_y", geo.y())
        self._config.set("window_width", geo.width())
        self._config.set("window_height", geo.height())
        super().closeEvent(ev)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background:{theme.BORDER}; }}")

        # Left: calendar
        self._calendar = CalendarWidget(self._config)
        splitter.addWidget(self._calendar)

        # Right: weather
        right = QWidget()
        right.setStyleSheet(f"background:{theme.BG};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(0)

        self._weather = WeatherWidget(self._config)
        right_layout.addWidget(self._weather, 0)
        right_layout.addStretch(1)
        splitter.addWidget(right)

        splitter.setSizes([950, 450])
        main_layout.addWidget(splitter)

        self._status = QStatusBar()
        self._status.setStyleSheet(
            f"background:{theme.SURFACE};color:{theme.SUBTEXT};font-size:8pt;"
        )
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    # ── menu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background:{theme.SURFACE}; color:{theme.TEXT}; }}"
            f"QMenuBar::item:selected {{ background:{theme.SURFACE2}; }}"
            f"QMenu {{ background:{theme.SURFACE}; color:{theme.TEXT}; "
            f"border:1px solid {theme.BORDER}; }}"
            f"QMenu::item:selected {{ background:{theme.BLUE}; color:{theme.BG}; }}"
        )

        file_menu = mb.addMenu("File")

        settings_action = QAction("Settings…", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = mb.addMenu("View")

        refresh_action = QAction("Refresh Weather", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._weather.refresh)
        view_menu.addAction(refresh_action)

    # ── settings ──────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self._config, self)
        if dlg.exec():
            lat = self._config.get("latitude")
            lon = self._config.get("longitude")
            city = self._config.get("city", "")
            country = self._config.get("country", "")
            if lat and lon:
                self._weather.set_location(lat, lon, city, country)
            self._calendar.reload()
            self._status.showMessage("Settings saved", 3000)

    # ── auto-location ─────────────────────────────────────────────────────

    def _auto_locate(self):
        if self._config.get("latitude") and self._config.get("longitude"):
            return
        self._loc_fetcher = _LocationFetcher()
        self._loc_fetcher.done.connect(self._on_location)
        self._loc_fetcher.start()
        self._status.showMessage("Detecting location…")

    def _on_location(self, loc):
        self._config.set("latitude", loc["lat"])
        self._config.set("longitude", loc["lon"])
        self._config.set("city", loc["city"])
        if not self._config.get("country"):
            self._config.set("country", loc["country_code"])
        if not self._config.get("subdivision"):
            self._config.set("subdivision", loc.get("region_code", ""))
        self._weather.set_location(
            loc["lat"], loc["lon"], loc["city"], loc["country_code"]
        )
        self._calendar.reload()
        self._status.showMessage(
            f"Location detected: {loc['city']}, {loc['country_code']}", 4000
        )
