from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

from plannerboard.ui import theme

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
    attribution: '© OpenStreetMap contributors',
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

  // RainViewer radar overlay
  fetch('https://api.rainviewer.com/public/weather-maps.json')
    .then(function(r) {{ return r.json(); }})
    .then(function(api) {{
      var frames = api.radar.past;
      if (frames.length === 0) return;
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


class RadarPanel(QWidget):
    def __init__(self, lat=51.5, lon=7.0, parent=None):
        super().__init__(parent)
        self._lat = lat
        self._lon = lon
        self._open = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(0)

        try:
            self._map = QWebEngineView()
            root.addWidget(self._map)
            self._map_available = True
        except Exception:
            fallback = QLabel("Radar requires PyQt6-WebEngine")
            fallback.setStyleSheet(f"color:{theme.SUBTEXT};padding:8px;")
            root.addWidget(fallback)
            self._map_available = False

        self.setMaximumHeight(COLLAPSED_H)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

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
            lat=self._lat, lon=self._lon,
            bg=theme.BG, blue=theme.BLUE,
        )
        self._map.setHtml(html, QUrl("https://localhost"))

    @property
    def is_open(self):
        return self._open
