import requests

WMO_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm+hail", 99: "Thunderstorm+hail",
}

WMO_ICONS = {
    0: "☀", 1: "🌤", 2: "⛅", 3: "☁",
    45: "🌫", 48: "🌫",
    51: "🌦", 53: "🌦", 55: "🌧",
    61: "🌧", 63: "🌧", 65: "🌧",
    71: "🌨", 73: "🌨", 75: "❄", 77: "❄",
    80: "🌦", 81: "🌧", 82: "⛈",
    85: "🌨", 86: "❄",
    95: "⛈", 96: "⛈", 99: "⛈",
}


def wmo_icon(code):
    return WMO_ICONS.get(code, "?")


def wmo_description(code):
    return WMO_DESCRIPTIONS.get(code, "Unknown")


def get_weather(lat, lon, unit="celsius", wind_unit="kmh"):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,apparent_temperature,weathercode,"
            "windspeed_10m,relativehumidity_2m,precipitation"
        ),
        "hourly": (
            "temperature_2m,weathercode,precipitation_probability,"
            "precipitation,windspeed_10m"
        ),
        "daily": (
            "weathercode,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,sunrise,sunset"
        ),
        "timezone": "auto",
        "forecast_days": 7,
        "temperature_unit": unit,
        "wind_speed_unit": wind_unit,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
