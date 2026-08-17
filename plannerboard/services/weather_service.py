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
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️", 77: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

# Background color used for the icon badge in the UI
WMO_BG_COLORS = {
    0:  "#f9e2af",  # clear – warm amber
    1:  "#f9e2af",
    2:  "#cba6f7",  # partly cloudy – lavender
    3:  "#585b70",  # overcast – grey
    45: "#6c7086",  # fog
    48: "#6c7086",
    51: "#89dceb",  # drizzle – sky blue
    53: "#89dceb",
    55: "#74c7ec",
    61: "#74c7ec",  # rain – blue
    63: "#74c7ec",
    65: "#89b4fa",
    71: "#cdd6f4",  # snow – pale blue
    73: "#cdd6f4",
    75: "#b4befe",
    77: "#cdd6f4",
    80: "#89dceb",  # showers
    81: "#74c7ec",
    82: "#89b4fa",
    85: "#cdd6f4",
    86: "#b4befe",
    95: "#cba6f7",  # thunderstorm – purple
    96: "#cba6f7",
    99: "#cba6f7",
}


def wmo_icon(code):
    return WMO_ICONS.get(code, "?")


def wmo_description(code):
    return WMO_DESCRIPTIONS.get(code, "Unknown")


def wmo_bg_color(code):
    return WMO_BG_COLORS.get(code, "#45475a")


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


def geocode(query, count=8):
    """Search for city names via Open-Meteo geocoding API. Returns list of result dicts."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": query, "count": count, "language": "en", "format": "json"}
    r = requests.get(url, params=params, timeout=8)
    r.raise_for_status()
    return r.json().get("results", [])
