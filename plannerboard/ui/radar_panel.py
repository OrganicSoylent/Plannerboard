import os
import tempfile

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QUrl

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

        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtWebEngineCore import QWebEngineSettings

            self._map = QWebEngineView()
            # Allow the local temp file to fetch external tile/API URLs
            self._map.page().settings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                True,
            )
            root.addWidget(self._map)
            self._map_available = True
        except Exception:
            fallback = QLabel("Radar requires PyQt6-WebEngine.\nInstall it with: pip install PyQt6-WebEngine")
            fallback.setStyleSheet(f"color:{theme.SUBTEXT};padding:12px;")
            fallback.setWordWrap(True)
            root.addWidget(fallback)

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
            lat=self._lat,
            lon=self._lon,
            bg=theme.BG,
            blue=theme.BLUE,
        )
        # Write to a local file so the page can load external CDN/API resources
        # (setHtml with a remote base URL blocks cross-origin tile fetches)
        with open(_TMP_HTML, "w", encoding="utf-8") as f:
            f.write(html)
        self._map.load(QUrl.fromLocalFile(_TMP_HTML))

    @property
    def is_open(self):
        return self._open
