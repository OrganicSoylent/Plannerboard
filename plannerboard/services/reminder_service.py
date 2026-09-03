import os
import subprocess

_SYSTEM_SOUNDS = [
    ("Alarm",    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"),
    ("Bell",     "/usr/share/sounds/freedesktop/stereo/bell.oga"),
    ("Complete", "/usr/share/sounds/freedesktop/stereo/complete.oga"),
    ("Message",  "/usr/share/sounds/freedesktop/stereo/message.oga"),
    ("Phone",    "/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"),
    ("Warning",  "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"),
]

_PLAYERS = ("paplay", "pw-play")


def get_available_sounds() -> list:
    """Return list of (label, path) for system sounds that actually exist."""
    return [(label, path) for label, path in _SYSTEM_SOUNDS if os.path.exists(path)]


def play_reminder_sound(sound_path: str | None = None):
    """Play sound_path if given and exists; otherwise try the first available system sound."""
    candidates = []
    if sound_path and os.path.exists(sound_path):
        candidates.append(sound_path)
    else:
        candidates.extend(path for _, path in get_available_sounds())

    for path in candidates:
        for player in _PLAYERS:
            try:
                subprocess.Popen(
                    [player, path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except FileNotFoundError:
                continue

    # Last resort: terminal bell
    print("\a", end="", flush=True)


def fire_reminder(event: dict, sound_path: str | None = None):
    title = event.get("title", "Event")
    ev_time = (event.get("time") or "")[:5]
    body = f"Today at {ev_time}" if ev_time else event.get("date", "")
    try:
        subprocess.Popen(
            ["notify-send", f"🔔 {title}", body,
             "--urgency=normal", "--icon=appointment-soon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
    play_reminder_sound(sound_path)
