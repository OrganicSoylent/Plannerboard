import os
import subprocess

# Freedesktop sound theme — present on virtually all Linux desktops
_SOUNDS = [
    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
    "/usr/share/sounds/freedesktop/stereo/bell.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/freedesktop/stereo/message.oga",
]

_PLAYERS = ("paplay", "pw-play")


def play_reminder_sound():
    for path in _SOUNDS:
        if not os.path.exists(path):
            continue
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


def fire_reminder(event: dict):
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
    play_reminder_sound()
