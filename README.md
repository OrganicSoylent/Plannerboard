# Plannerboard

A personal organizing dashboard for Linux desktop (optimized for Bazzite/KDE Plasma).

## Features

- **Calendar** — Day, Week, Month, and Year views. Add events and reminders with colors, times, and notes. Public holidays shown automatically for your country/region.
- **Weather** — Compact panel with current conditions, 24-hour chart, and 7-day forecast. Powered by [Open-Meteo](https://open-meteo.com) (free, no API key required).
- **Radar** — Live rain/cloud radar map (50 km radius) that slides open on demand. Powered by RainViewer + OpenStreetMap.

## Requirements

- Python 3.11+
- Linux desktop with a Wayland or X11 session

## Setup

```bash
bash setup.sh
```

Then run:

```bash
.venv/bin/python run.py
```

## Autostart on login

Open the app → **File → Settings** → enable **"Launch Plannerboard on login"**.

This writes a `.desktop` file to `~/.config/autostart/plannerboard.desktop`.

## Personal data

All your data stays off the repo:

| What | Where |
|---|---|
| Calendar events | `~/.local/share/plannerboard/events.db` |
| Settings (location, country…) | `~/.config/plannerboard/config.json` |

## First launch

On first launch the app auto-detects your location via IP geolocation. You can override or fine-tune everything under **File → Settings**.
