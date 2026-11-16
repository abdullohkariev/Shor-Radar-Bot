from ..rules import val
from .crops import CROPS, DRY_WETNESS, WATCH_WETNESS, MAX_DEFICIT_MM
from .et import row_et0


def effective_rain(mm: float) -> float:
    """Simple rule: light showers (<3 mm) are lost, otherwise 75% is effective."""
    return 0.0 if mm < val("eff_rain_min_mm") else val("eff_rain_frac") * mm


def water_balance(series: list[dict], lat: float, kc: float, days: int = 7) -> dict:
    """Crop water use minus effective rain over the last `days` days (7 by default; fewer after a logged irrigation)."""
    window = series[-days:] if days > 0 else []
    crop_et = sum(row_et0(r, lat) for r in window) * kc
    rain = sum(effective_rain(r["PRECTOTCORR"] or 0.0) for r in window)
    last7 = series[-7:]
    et0_mean = sum(row_et0(r, lat) for r in last7) / max(len(last7), 1)
    wets = [r["GWETROOT"] for r in series[-3:] if r.get("GWETROOT") is not None]
    return {"et0_mean": et0_mean, "crop_et": crop_et, "eff_rain": rain,
            "deficit": max(0.0, crop_et - rain), "root_wetness": sum(wets) / len(wets) if wets else None}


def irrigation_advice(series, forecast, crop: str, stage: str, lat: float, since_irrigation: int | None = None) -> dict:
    """`since_irrigation` = days since the farmer LOGGED an irrigation (0 = today), None if never logged.
    Satellite/model soil wetness cannot see irrigation water, so a logged irrigation is the only way the advice learns of it."""
    if stage == "fallow":
        return {"status": "WAIT", "reason_key": "irr_fallow", "params": {}, "metrics": {}}
    kc = CROPS[crop]["kc"][stage]
    window = 7 if since_irrigation is None else max(0, min(7, since_irrigation))      # deficit counts only since the last irrigation
    m = water_balance(series, lat, kc, window)
    rain3 = round(sum(f["rain"] for f in (forecast or [])[:3]), 1)
    wet, deficit = m["root_wetness"], m["deficit"]
    metrics = {"root_wetness": None if wet is None else round(wet, 2), "deficit_mm": round(deficit, 1),
               "et0_mm_day": round(m["et0_mean"], 1), "kc": kc, "rain_next3d_mm": rain3,
               "forecast_available": forecast is not None, "days_since_irrigation": since_irrigation}

    if since_irrigation is not None and since_irrigation <= val("irrigation_hold_days"):
        status, key = "WAIT", "irr_recent"
    elif rain3 >= val("wait_rain_mm"):
        status, key = "WAIT", "irr_rain"
    elif (wet is not None and wet < DRY_WETNESS) or deficit > MAX_DEFICIT_MM:
        status, key = "IRRIGATE", ("irr_dry" if wet is not None and wet < DRY_WETNESS else "irr_deficit")
    elif (wet is not None and wet < WATCH_WETNESS) or deficit > val("watch_deficit_frac") * MAX_DEFICIT_MM:
        status, key = "MONITOR", "irr_watch"
    else:
        status, key = "WAIT", "irr_ok"
    return {"status": status, "reason_key": key,
            "params": {"rain": rain3, "deficit": round(deficit, 1), "n": since_irrigation}, "metrics": metrics}
