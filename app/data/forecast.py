"""7-day forecast from Open-Meteo (no key). NASA POWER has no forecast."""
import datetime as dt
import time

import httpx

from ..config import OPEN_METEO_URL


_CACHE: dict = {}
TTL = 3600
META = {"accessed": None}


def invalidate(lat: float, lon: float):
    _CACHE.pop((round(lat, 1), round(lon, 1)), None)


async def fetch_forecast(lat: float, lon: float, client=None):
    """Returns [{date, rain, tmax, tmin}] or None if the service is unreachable."""
    key = (round(lat, 1), round(lon, 1))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    params = {"latitude": lat, "longitude": lon, "forecast_days": 7, "timezone": "auto",
              "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        r = await client.get(OPEN_METEO_URL, params=params)
        r.raise_for_status()
        d = r.json()["daily"]
        rows = [{"date": dt.date.fromisoformat(t), "rain": d["precipitation_sum"][i] or 0.0,
                 "tmax": d["temperature_2m_max"][i], "tmin": d["temperature_2m_min"][i]}
                for i, t in enumerate(d["time"])]
        _CACHE[key] = (time.time(), rows)
        META["accessed"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        return rows
    except Exception:
        return None
    finally:
        if own:
            await client.aclose()
