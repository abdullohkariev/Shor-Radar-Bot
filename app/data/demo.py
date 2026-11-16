"""Deterministic synthetic data so the whole app runs offline (demo / tests / no internet).
NOT real measurements. The API labels such responses source='demo'."""
import datetime as dt
import math
import random


def _rng(lat, lon):
    return random.Random(int(lat * 100) * 100003 + int(lon * 100))


def _tmean(doy, lat):
    return 14 - 15 * math.cos(2 * math.pi * (doy - 15) / 365) + (41 - lat) * 0.6


def demo_power(lat, lon, days=90):
    rng = _rng(lat, lon)
    today = dt.date.today()
    wet_root = rng.uniform(0.18, 0.6)
    wet_top = wet_root
    rows = []
    for i in range(days, 0, -1):
        d = today - dt.timedelta(days=i)
        tm = _tmean(d.timetuple().tm_yday, lat) + rng.uniform(-2, 2)
        rain = rng.uniform(0, 12) if rng.random() < 0.12 else 0.0
        wet_root = min(0.8, max(0.1, wet_root + (0.03 if rain > 2 else -0.004) + rng.uniform(-0.004, 0.004)))
        wet_top = min(0.85, max(0.05, wet_top + (0.08 if rain > 2 else -0.015) + rng.uniform(-0.01, 0.01)))
        rows.append({"date": d, "T2M": tm, "T2M_MAX": tm + 7, "T2M_MIN": tm - 7,
                     "PRECTOTCORR": rain, "RH2M": 45.0, "ALLSKY_SFC_SW_DWN": 10.0,
                     "GWETROOT": wet_root, "GWETTOP": wet_top})
    return rows


def demo_forecast(lat, lon):
    rng = _rng(lat, lon + 1)
    today = dt.date.today()
    out = []
    for i in range(1, 8):
        tm = _tmean((today + dt.timedelta(days=i)).timetuple().tm_yday, lat)
        out.append({"date": today + dt.timedelta(days=i),
                    "rain": rng.uniform(0, 14) if rng.random() < 0.15 else 0.0,
                    "tmax": tm + 6, "tmin": tm - 6})
    return out
