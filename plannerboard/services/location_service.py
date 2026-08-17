import requests


def get_location():
    """Detect current location via IP. Returns dict or None on failure."""
    try:
        r = requests.get("http://ip-api.com/json", timeout=5)
        d = r.json()
        if d.get("status") == "success":
            return {
                "lat": d["lat"],
                "lon": d["lon"],
                "city": d["city"],
                "country_code": d["countryCode"],
                "timezone": d["timezone"],
                "region": d.get("region", ""),
                "region_code": d.get("regionCode", ""),
            }
    except Exception:
        pass
    return None
