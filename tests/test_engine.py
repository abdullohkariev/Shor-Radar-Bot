import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.data.nasa_power import parse_power
from app.engine.advisor import build_advice
from app.engine.crops import recommend
from app.engine.et import hargreaves_et0
from app.engine.flush import flush_guidance
from app.engine.irrigation import irrigation_advice
from app.engine.salinity import salinity_risk

LAT = 41.5


def series(n=30, wet=0.5, rain=0.0, tmax=14.0, tmin=3.0, start=dt.date(2026, 11, 1)):
    return [{"date": start + dt.timedelta(days=i), "T2M": (tmax + tmin) / 2, "T2M_MAX": tmax, "T2M_MIN": tmin,
             "PRECTOTCORR": rain, "RH2M": 50, "ALLSKY_SFC_SW_DWN": 8, "GWETROOT": wet, "GWETTOP": wet}
            for i in range(n)]


def fc(rain=0.0, tmin=3.0):
    return [{"date": dt.date(2026, 12, 1) + dt.timedelta(days=i), "rain": rain, "tmax": 12, "tmin": tmin} for i in range(7)]


def test_et0_plausible():
    assert 5.5 < hargreaves_et0(35, 20, 41, 190) < 8.5   # Tashkent July
    assert hargreaves_et0(10, 2, 41, 320) < 2.0          # November


def test_irrigation_rules():
    assert irrigation_advice(series(wet=0.2), fc(), "cotton", "mid", LAT)["status"] == "IRRIGATE"
    assert irrigation_advice(series(wet=0.2), fc(rain=4), "cotton", "mid", LAT)["status"] == "WAIT"  # 12 mm in 3 d
    assert irrigation_advice(series(wet=0.4), fc(), "cotton", "mid", LAT)["status"] == "MONITOR"
    assert irrigation_advice(series(wet=0.6), fc(), "cotton", "mid", LAT)["status"] == "WAIT"
    assert irrigation_advice(series(wet=0.1), fc(), "cotton", "fallow", LAT)["status"] == "WAIT"


def test_irrigation_without_forecast_or_wetness():
    s = series(wet=0.2)
    assert irrigation_advice(s, None, "wheat", "mid", LAT)["metrics"]["forecast_available"] is False
    for r in s:
        r["GWETROOT"] = None
    assert irrigation_advice(s, None, "wheat", "mid", LAT)["status"] in {"WAIT", "MONITOR", "IRRIGATE"}


def test_salinity_levels():
    dry = series(n=90, rain=0.0, tmax=36, tmin=20, start=dt.date(2026, 6, 1))
    assert salinity_risk(dry, LAT, "shallow", None)["level"] == "HIGH"
    wet = series(n=90, rain=8.0, start=dt.date(2026, 9, 1))
    assert salinity_risk(wet, LAT, "deep", 30)["level"] == "LOW"


def test_flush_rules():
    s = series()
    assert flush_guidance(s, fc(), "LOW", "good", LAT)["status"] == "NOT_NEEDED"
    assert flush_guidance(s, fc(), "HIGH", "poor", LAT)["status"] == "NOT_ADVISED"
    assert flush_guidance(s, fc(tmin=-6), "HIGH", "good", LAT)["status"] == "NOT_NOW"
    assert flush_guidance(s, fc(rain=6), "HIGH", "good", LAT)["status"] == "NOT_NOW"
    assert flush_guidance(series(tmax=34, tmin=20, start=dt.date(2026, 7, 1)), fc(), "HIGH", "good", LAT)["status"] == "NOT_NOW"
    assert flush_guidance(s, fc(), "HIGH", "good", LAT)["status"] == "CONSIDER"
    assert flush_guidance(s, fc(), "HIGH", "unknown", LAT)["reason_key"] == "flush_consider_unknown_drainage"


def test_crops():
    fits = {c["crop"]: c["fit"] for c in recommend("HIGH")["crops"]}
    assert fits["barley"] == "good" and fits["maize"] == "avoid" and fits["onion"] == "avoid"
    assert recommend("LOW", "high")["level"] == "HIGH"   # user report can raise the level
    assert recommend("HIGH", "low")["level"] == "HIGH"   # but never lower it


def test_parse_power_handles_missing():
    d = {p: {"20261101": 1.0, "20261102": -999} for p in
         ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN", "GWETROOT", "GWETTOP"]}
    rows = parse_power(d)
    assert len(rows) == 1 and rows[0]["GWETROOT"] == 1.0


def test_build_advice_shape():
    a = build_advice(series(), fc(), LAT, 60.6)
    assert {"irrigation", "salinity", "flush", "crops", "data"} <= a.keys()
    with pytest.raises(ValueError):
        build_advice(series(), fc(), LAT, 60.6, crop="banana")


def test_api_demo_mode_all_languages():
    from app.main import app
    c = TestClient(app)
    for lang in ("en", "uz", "ru"):
        r = c.get("/api/advice", params={"lat": 41.55, "lon": 60.63, "lang": lang, "demo": True})
        assert r.status_code == 200 and r.json()["text"]["message"]
    assert c.get("/api/advice", params={"lat": 41.5, "lon": 60.6, "crop": "banana", "demo": True}).status_code == 422
    assert c.get("/api/advice", params={"lat": 10, "lon": 60.6}).status_code == 422
    m = c.get("/api/map", params={"demo": True}).json()
    assert len(m) == 8 and all("advice" in f for f in m)
    assert c.get("/").status_code == 200
