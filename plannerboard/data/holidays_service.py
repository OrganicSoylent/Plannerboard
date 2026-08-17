import holidays as _holidays_lib


def get_holidays(year, country="DE", subdiv=None):
    """Returns {date: holiday_name} for the given year/country/subdivision."""
    try:
        h = _holidays_lib.country_holidays(country, subdiv=subdiv, years=year)
        return dict(h)
    except Exception:
        return {}


def list_subdivisions(country):
    """Returns list of available subdivision codes for a country."""
    try:
        return sorted(_holidays_lib.country_holidays(country).subdivisions)
    except Exception:
        return []


def list_countries():
    """Returns list of supported country codes."""
    try:
        return sorted(_holidays_lib.list_supported_countries().keys())
    except Exception:
        return []
