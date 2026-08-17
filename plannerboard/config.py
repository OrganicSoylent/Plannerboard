import json
import platform
from pathlib import Path

if platform.system() == "Linux":
    DATA_DIR = Path.home() / ".local" / "share" / "plannerboard"
    CONFIG_DIR = Path.home() / ".config" / "plannerboard"
else:
    DATA_DIR = Path.home() / "AppData" / "Local" / "plannerboard"
    CONFIG_DIR = Path.home() / "AppData" / "Roaming" / "plannerboard"

DEFAULTS = {
    "country": "DE",
    "subdivision": "NW",
    "latitude": None,
    "longitude": None,
    "city": None,
    "timezone": "auto",
    "temperature_unit": "celsius",
    "wind_speed_unit": "kmh",
    "autostart": False,
    "window_x": None,
    "window_y": None,
    "window_width": 1400,
    "window_height": 900,
}


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._path = CONFIG_DIR / "config.json"
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self.set(key, value)
