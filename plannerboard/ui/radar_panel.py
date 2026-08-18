import os
import sys
import tempfile

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QUrl

from plannerboard.ui import theme

# ── WebEngine availability check (done once at import time) ────────────────
_WE_ERROR = ""
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings as _QWebEngineSettings
    _WE_AVAILABLE = True
except Exception as _e:
    _WE_AVAILABLE = False
    _WE_ERROR = str(_e)

# ── Radar HTML template ────────────────────────────────────────────────────

RADAR_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:{bg}; }}
  #map {{ width:100%; height:100vh; }}
</style>
<link rel="stylesheet"
  href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
<div id="map"></div>
<script>
  var LAT = {lat};
  var LON = {lon};
  var map = L.map('map', {{ zoomControl: true }}).setView([LAT, LON], 9);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18
  }}).addTo(map);

  L.circle([LAT, LON], {{
    color: '{blue}',
    fillColor: '{blue}',
    fillOpacity: 0.04,
    radius: 50000,
    weight: 1.5,
    dashArray: '6 4'
  }}).addTo(map);

  L.marker([LAT, LON])
    .bindPopup('You are here')
    .addTo(map);

  fetch('https://api.rainviewer.com/public/weather-maps.json')
    .then(function(r) {{ return r.json(); }})
    .then(function(api) {{
      var frames = api.radar.past;
      if (!frames || frames.length === 0) return;
      var latest = frames[frames.length - 1];
      var url = api.host + latest.path + '/512/{{z}}/{{x}}/{{y}}/2/1_1.png';
      L.tileLayer(url, {{
        tileSize: 512,
        opacity: 0.55,
        zIndex: 2,
        attribution: 'RainViewer'
      }}).addTo(map);
    }})
    .catch(function() {{}});
</script>
</body>
</html>
"""

COLLAPSED_H = 0
EXPANDED_H = 360
_TMP_HTML = os.path.join(tempfile.gettempdir(), "plannerboard_radar.html")


class RadarPanel(QWidget):
    def __init__(self, lat=51.5, lon=7.0, parent=None):
        super().__init__(parent)
        self._lat = lat
        self._lon = lon
        self._open = False
        self._map_available = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(0)

        if _WE_AVAILABLE:
            try:
                self._map = _QWebEngineView()

                # Allow local temp file to load external CDN / tile URLs
                try:
                    self._map.page().settings().setAttribute(
                        _QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                        True,
                    )
                except Exception:
                    pass  # setting may not exist in all PyQt6-WebEngine versions

                root.addWidget(self._map)
                self._map_available = True
            except Exception as e:
                self._show_fallback(root, f"WebEngine init error:\n{e}\n\n"
                                   "Try running:\n"
                                   "  QTWEBENGINE_DISABLE_SANDBOX=1 python run.py")
        else:
            self._show_fallback(root, f"PyQt6-WebEngine import failed:\n{_WE_ERROR}\n\n"
                               "Install with:\n"
                               "  pip install PyQt6-WebEngine")

        self.setMaximumHeight(COLLAPSED_H)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _show_fallback(self, layout, msg):
        lbl = QLabel(msg)
        lbl.setStyleSheet(
            f"color:{theme.SUBTEXT};padding:12px;font-size:9pt;"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def set_location(self, lat, lon):
        self._lat = lat
        self._lon = lon
        if self._open and self._map_available:
            self._load_map()

    def toggle(self):
        if self._open:
            self._anim.setStartValue(self.maximumHeight())
            self._anim.setEndValue(COLLAPSED_H)
        else:
            if self._map_available:
                self._load_map()
            self._anim.setStartValue(COLLAPSED_H)
            self._anim.setEndValue(EXPANDED_H)
        self._open = not self._open
        self._anim.start()
        return self._open

    def _load_map(self):
        html = RADAR_HTML.format(
            lat=self._lat,
            lon=self._lon,
            bg=theme.BG,
            blue=theme.BLUE,
        )
        with open(_TMP_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        self._map.load(QUrl.fromLocalFile(_TMP_HTML))

    @property
    def is_open(self):
        return self._open
