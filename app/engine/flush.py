"""Qualified salt-flushing (leaching) timing guidance. Never a firm instruction."""
from ..rules import val
from .et import row_et0


def flush_guidance(series, forecast, level: str, drainage: str, lat: float, water_ec: float | None = None) -> dict:
    if level == "LOW":
        return {"status": "NOT_NEEDED", "reason_key": "flush_not_needed", "params": {}}
    if drainage == "poor":
        return {"status": "NOT_ADVISED", "reason_key": "flush_drainage", "params": {}}

    if water_ec is not None and water_ec >= val("water_ec_limit"):
        return {"status": "NOT_ADVISED", "reason_key": "flush_saline_water", "params": {"ec": round(water_ec, 1)}}

    fc = forecast or []
    recent_tmin = min((r["T2M_MIN"] for r in series[-3:]), default=5)
    next_tmin = min((f["tmin"] for f in fc[:3] if f["tmin"] is not None), default=5)
    rain3 = sum(f["rain"] for f in fc[:3])
    et0_mean = sum(row_et0(r, lat) for r in series[-7:]) / max(len(series[-7:]), 1)

    if min(recent_tmin, next_tmin) <= val("flush_frost_c"):
        return {"status": "NOT_NOW", "reason_key": "flush_frost", "params": {}}
    if rain3 >= val("flush_rain_mm"):
        return {"status": "NOT_NOW", "reason_key": "flush_rain", "params": {"rain": round(rain3, 1)}}
    if et0_mean > val("flush_et_mm"):
        return {"status": "NOT_NOW", "reason_key": "flush_high_et", "params": {"et0": round(et0_mean, 1)}}
    key = "flush_consider_unknown_drainage" if drainage == "unknown" else "flush_consider"
    return {"status": "CONSIDER", "reason_key": key, "params": {"et0": round(et0_mean, 1)}}
