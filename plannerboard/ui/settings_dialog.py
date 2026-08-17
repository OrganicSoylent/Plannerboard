import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QDialogButtonBox,
    QGroupBox, QFormLayout, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

from plannerboard.data.holidays_service import list_countries, list_subdivisions


def _autostart_path():
    return Path.home() / ".config" / "autostart" / "plannerboard.desktop"


def _script_dir():
    import plannerboard
    return Path(plannerboard.__file__).parent.parent.resolve()


def _write_desktop(script_dir):
    venv_python = script_dir / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else "python3"
    entry_point = script_dir / "run.py"
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Plannerboard\n"
        "Comment=Organizing Life Dashboard\n"
        f"Exec={python} {entry_point}\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    path = _autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _remove_desktop():
    p = _autostart_path()
    if p.exists():
        p.unlink()


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ── Location ──────────────────────────────────────────────────────
        loc_box = QGroupBox("Location")
        lf = QFormLayout(loc_box)

        self._city_edit = QLineEdit(self._config.get("city") or "")
        self._city_edit.setPlaceholderText("City name (display only)")
        lf.addRow("City:", self._city_edit)

        self._lat_spin = QDoubleSpinBox()
        self._lat_spin.setRange(-90, 90)
        self._lat_spin.setDecimals(4)
        self._lat_spin.setValue(self._config.get("latitude") or 0.0)
        lf.addRow("Latitude:", self._lat_spin)

        self._lon_spin = QDoubleSpinBox()
        self._lon_spin.setRange(-180, 180)
        self._lon_spin.setDecimals(4)
        self._lon_spin.setValue(self._config.get("longitude") or 0.0)
        lf.addRow("Longitude:", self._lon_spin)

        detect_btn = QPushButton("Auto-detect from IP")
        detect_btn.clicked.connect(self._detect_location)
        lf.addRow("", detect_btn)
        root.addWidget(loc_box)

        # ── Holidays ──────────────────────────────────────────────────────
        hol_box = QGroupBox("Public Holidays")
        hf = QFormLayout(hol_box)

        self._country_cb = QComboBox()
        countries = list_countries()
        self._country_cb.addItems(countries)
        current_c = self._config.get("country", "DE")
        if current_c in countries:
            self._country_cb.setCurrentText(current_c)
        self._country_cb.currentTextChanged.connect(self._reload_subdivisions)
        hf.addRow("Country:", self._country_cb)

        self._subdiv_cb = QComboBox()
        hf.addRow("State/Region:", self._subdiv_cb)
        self._reload_subdivisions(current_c)

        current_s = self._config.get("subdivision", "")
        if current_s:
            idx = self._subdiv_cb.findText(current_s)
            if idx >= 0:
                self._subdiv_cb.setCurrentIndex(idx)

        root.addWidget(hol_box)

        # ── Units ─────────────────────────────────────────────────────────
        unit_box = QGroupBox("Units")
        uf = QFormLayout(unit_box)

        self._temp_cb = QComboBox()
        self._temp_cb.addItems(["celsius", "fahrenheit"])
        self._temp_cb.setCurrentText(self._config.get("temperature_unit", "celsius"))
        uf.addRow("Temperature:", self._temp_cb)

        self._wind_cb = QComboBox()
        self._wind_cb.addItems(["kmh", "mph", "ms", "knots"])
        self._wind_cb.setCurrentText(self._config.get("wind_speed_unit", "kmh"))
        uf.addRow("Wind speed:", self._wind_cb)
        root.addWidget(unit_box)

        # ── Autostart (Linux only) ────────────────────────────────────────
        if platform.system() == "Linux":
            auto_box = QGroupBox("Autostart")
            af = QFormLayout(auto_box)
            self._autostart_cb = QCheckBox("Launch Plannerboard on login")
            self._autostart_cb.setChecked(_autostart_path().exists())
            af.addRow(self._autostart_cb)
            root.addWidget(auto_box)
        else:
            self._autostart_cb = None

        # ── Buttons ───────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _reload_subdivisions(self, country):
        self._subdiv_cb.clear()
        self._subdiv_cb.addItem("(none)", "")
        for s in list_subdivisions(country):
            self._subdiv_cb.addItem(s, s)

    def _detect_location(self):
        from plannerboard.services.location_service import get_location
        loc = get_location()
        if loc:
            self._lat_spin.setValue(loc["lat"])
            self._lon_spin.setValue(loc["lon"])
            self._city_edit.setText(loc["city"])
            if loc["country_code"] in [self._country_cb.itemText(i)
                                        for i in range(self._country_cb.count())]:
                self._country_cb.setCurrentText(loc["country_code"])
            rs = loc.get("region_code", "")
            if rs:
                idx = self._subdiv_cb.findText(rs)
                if idx >= 0:
                    self._subdiv_cb.setCurrentIndex(idx)

    def _save(self):
        self._config.set("city", self._city_edit.text().strip())
        self._config.set("latitude", self._lat_spin.value())
        self._config.set("longitude", self._lon_spin.value())
        self._config.set("country", self._country_cb.currentText())
        self._config.set("subdivision", self._subdiv_cb.currentData() or "")
        self._config.set("temperature_unit", self._temp_cb.currentText())
        self._config.set("wind_speed_unit", self._wind_cb.currentText())

        if self._autostart_cb is not None:
            if self._autostart_cb.isChecked():
                try:
                    _write_desktop(_script_dir())
                except Exception:
                    pass
            else:
                _remove_desktop()

        self.accept()
