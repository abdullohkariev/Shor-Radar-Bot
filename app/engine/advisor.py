from .. import config
from ..data.demo import demo_forecast, demo_power
from ..data.forecast import fetch_forecast, invalidate as invalidate_forecast
from ..data.nasa_power import fetch_power, invalidate as invalidate_power
from .crops import CROPS, STAGES, recommend
from .flush import flush_guidance
from .irrigation import irrigation_advice
from .plan import build_plan
from .salinity import salinity_risk


def build_advice(series, forecast, lat, lon, crop="cotton", stage="mid", groundwater="unknown",
                 drainage="unknown", last_flush_days=None, ec_class=None, source="NASA POWER", ece=None, water_ec=None, since_irrigation=None) -> dict:
    """Pure function: all rules in one place, easy to unit-test."""
    if crop not in CROPS:
        raise ValueError(f"unknown crop {crop}")
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage}")
    irr = irrigation_advice(series, forecast, crop, stage, lat, since_irrigation)
    sal = salinity_risk(series, lat, groundwater, last_flush_days, ec_class)
    rec = recommend(sal["level"], ec_class, ece)
    fl = flush_guidance(series, forecast, rec["level"], drainage, lat, water_ec)
    return {
        "location": {"lat": lat, "lon": lon}, "crop": crop, "stage": stage,
        "irrigation": irr, "salinity": sal, "flush": fl, "crops": rec,
        "data": {"source": source, "last_date": series[-1]["date"].isoformat() if series else None,
                 "forecast": forecast is not None, "grid_note": "NASA POWER ~0.5 degree grid"},
    }


async def get_advice(lat, lon, demo=None, **kw) -> dict:
    demo = config.DEMO_MODE if demo is None else demo
    if demo:
        return build_advice(demo_power(lat, lon), demo_forecast(lat, lon), lat, lon, source="demo", **kw)
    series = await fetch_power(lat, lon)
    if not series:
        raise RuntimeError("NASA POWER returned no data")
    forecast = await fetch_forecast(lat, lon)
    return build_advice(series, forecast, lat, lon, **kw)


async def get_snapshot(lat, lon, demo=None, refresh=False):
    """(series, forecast) for the dashboard. refresh=True drops the cache first (Refresh button)."""
    demo = config.DEMO_MODE if demo is None else demo
    if demo:
        return demo_power(lat, lon), demo_forecast(lat, lon)
    if refresh:
        invalidate_power(lat, lon)
        invalidate_forecast(lat, lon)
    return await fetch_power(lat, lon), await fetch_forecast(lat, lon)


async def get_plan(lat, lon, demo=None, **kw) -> dict:
    """Season outlook from ~2 years of past NASA POWER data (climatology, not a forecast)."""
    demo = config.DEMO_MODE if demo is None else demo
    series = demo_power(lat, lon, days=730) if demo else await fetch_power(lat, lon, days=730)
    if not series:
        raise RuntimeError("NASA POWER returned no data")
    plan = build_plan(series, lat, **kw)
    plan["source"] = "demo" if demo else "NASA POWER"
    return plan
