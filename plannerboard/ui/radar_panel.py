import tempfile
from pathlib import Path

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QUrl, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from plannerboard.config import DATA_DIR
from plannerboard.ui import theme

# ── WebEngine availability ─────────────────────────────────────────────────
_WE_ERROR = ""
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEngineSettings as _QWebEngineSettings,
        QWebEngineProfile as _QWebEngineProfile,
    )
    _WE_AVAILABLE = True
except Exception as _e:
    _WE_AVAILABLE = False
    _WE_ERROR = str(_e)

# ── Local Leaflet resource paths ───────────────────────────────────────────
_RES_DIR = DATA_DIR / "resources" / "leaflet"
_LEAFLET_CSS = _RES_DIR / "leaflet.min.css"
_LEAFLET_JS = _RES_DIR / "leaflet.min.js"
_LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
_LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.min.js"

_TMP_HTML = Path(tempfile.gettempdir()) / "plannerboard_radar.html"

COLLAPSED_H = 0
EXPANDED_H = 380


def _leaflet_ready() -> bool:
    return _LEAFLET_CSS.exists() and _LEAFLET_JS.exists()


# Radar map HTML. Uses string .replace() markers (not .format()) so that the
# Leaflet JS source (full of { }) isn't misread as format placeholders.
# The actual substitutions happen in _build_html() below.
_RADAR_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body { width:100%; height:100%; background:__BG__; }
  #map { width:100%; height:100%; }
</style>
<link rel="stylesheet" href="__LEAFLET_CSS__">
<script src="__LEAFLET_JS__"></script>
</head>
<body>
<div id="map"></div>
<script>
  var map = L.map('map', {zoomControl: true}).setView([__LAT__, __LON__], 9);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18
  }).addTo(map);

  L.circle([__LAT__, __LON__], {
    color: '__BLUE__',
    fillColor: '__BLUE__',
    fillOpacity: 0.04,
    radius: 50000,
    weight: 1.5,
    dashArray: '6 4'
  }).addTo(map);

  L.marker([__LAT__, __LON__]).bindPopup('You are here').addTo(map);

  fetch('https://api.rainviewer.com/public/weather-maps.json')
    .then(function(r) { return r.json(); })
    .then(function(api) {
      var frames = api.radar.past;
      if (!frames || frames.length === 0) return;
      var latest = frames[frames.length - 1];
      var url = api.host + latest.path + '/512/{z}/{x}/{y}/2/1_1.png';
      L.tileLayer(url, {
        tileSize: 512,
        opacity: 0.55,
        zIndex: 2,
        attribution: 'RainViewer'
      }).addTo(map);
    })
    .catch(function() {});
</script>
</body>
</html>
"""


def _build_html(lat, lon):
    css_qurl = QUrl.fromLocalFile(str(_LEAFLET_CSS)).toString()
    js_qurl = QUrl.fromLocalFile(str(_LEAFLET_JS)).toString()
    return (
        _RADAR_HTML_TEMPLATE
        .replace("__LAT__", str(lat))
        .replace("__LON__", str(lon))
        .replace("__BG__", theme.BG)
        .replace("__BLUE__", theme.BLUE)
        .replace("__LEAFLET_CSS__", css_qurl)
        .replace("__LEAFLET_JS__", js_qurl)
    )


# ── Background downloader ──────────────────────────────────────────────────

class _LeafletDownloader(QThread):
    done = pyqtSignal(bool, str)  # ok, error_msg

    def run(self):
        try:
            import requests
            _RES_DIR.mkdir(parents=True, exist_ok=True)
            for path, url in [
                (_LEAFLET_CSS, _LEAFLET_CSS_URL),
                (_LEAFLET_JS, _LEAFLET_JS_URL),
            ]:
                if not path.exists():
                    r = requests.get(url, timeout=20)
                    r.raise_for_status()
                    path.write_bytes(r.content)
            self.done.emit(True, "")
        except Exception as exc:
            self.done.emit(False, str(exc))


# ── Main widget ────────────────────────────────────────────────────────────

class RadarPanel(QWidget):
    def __init__(self, lat=51.5, lon=7.0, parent=None):
        super().__init__(parent)
        self._lat = lat
        self._lon = lon
        self._open = False
        self._map_available = False
        self._map_loaded = False
        self._downloader: _LeafletDownloader | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if _WE_AVAILABLE:
            try:
                # Apply remote-URL access to the default profile so every page
                # (including the file:// radar page) can reach tile servers.
                try:
                    prof = _QWebEngineProfile.defaultProfile()
                    prof.settings().setAttribute(
                        _QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                        True,
                    )
                    prof.settings().setAttribute(
                        _QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                        True,
                    )
                except Exception:
                    pass

                self._map = _QWebEngineView()
                self._map.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
                self._map.loadFinished.connect(self._on_load_finished)

                # Belt-and-suspenders: also set per-page
                try:
                    s = self._map.page().settings()
                    s.setAttribute(
                        _QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                        True,
                    )
                    s.setAttribute(
                        _QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                        True,
                    )
                except Exception:
                    pass

                root.addWidget(self._map)
                self._map_available = True
            except Exception as exc:
                self._show_fallback(root, f"WebEngine init error:\n{exc}")
        else:
            self._show_fallback(
                root,
                f"PyQt6-WebEngine not available:\n{_WE_ERROR}\n\n"
                "Run:  pip install PyQt6-WebEngine",
            )

        self.setMaximumHeight(COLLAPSED_H)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        # Load only after animation ends so the view has a real non-zero size.
        self._anim.finished.connect(self._on_anim_finished)

    # ── helpers ────────────────────────────────────────────────────────────

    def _show_fallback(self, layout, msg: str):
        lbl = QLabel(msg)
        lbl.setStyleSheet(f"color:{theme.SUBTEXT};padding:12px;font-size:9pt;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

    def _status_html(self, msg: str) -> str:
        return (
            f"<html><body style='background:{theme.BG};color:{theme.TEXT};"
            f"font-family:sans-serif;display:flex;align-items:center;"
            f"justify-content:center;height:100%;margin:0;'>"
            f"<p>{msg}</p></body></html>"
        )

    # ── signal handlers ────────────────────────────────────────────────────

    def _on_load_finished(self, ok: bool):
        print(f"[Radar] load finished: ok={ok}  url={self._map.url().toString()}")

    def _on_anim_finished(self):
        if self._open and self._map_available and not self._map_loaded:
            self._trigger_load()

    def _trigger_load(self):
        if _leaflet_ready():
            self._do_load()
        else:
            self._map.setHtml(self._status_html("Downloading map library…"))
            self._downloader = _LeafletDownloader()
            self._downloader.done.connect(self._on_download_done)
            self._downloader.start()

    def _on_download_done(self, ok: bool, err: str):
        self._downloader = None
        if ok:
            self._do_load()
        else:
            self._map.setHtml(
                self._status_html(f"<span style='color:#f38ba8;'>Download failed: {err}</span>")
            )

    def _do_load(self):
        html = _build_html(self._lat, self._lon)
        _TMP_HTML.write_text(html, encoding="utf-8")
        self._map.load(QUrl.fromLocalFile(str(_TMP_HTML)))
        self._map_loaded = True

    # ── public API ─────────────────────────────────────────────────────────

    def set_location(self, lat: float, lon: float):
        self._lat = lat
        self._lon = lon
        self._map_loaded = False
        if self._open and self._map_available:
            self._trigger_load()

    def toggle(self) -> bool:
        if self._open:
            self._anim.setStartValue(self.maximumHeight())
            self._anim.setEndValue(COLLAPSED_H)
        else:
            self._anim.setStartValue(COLLAPSED_H)
            self._anim.setEndValue(EXPANDED_H)
        self._open = not self._open
        self._anim.start()
        return self._open

    @property
    def is_open(self) -> bool:
        return self._open
