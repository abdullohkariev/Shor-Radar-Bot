"""Salinity RISK indicator (not a measurement). NASA weather data cannot see salt directly;
we score conditions that favour salt build-up in the root zone. Weights are placeholders
to be reviewed by the research team."""
from ..rules import val
from .et import row_et0


def salinity_risk(series, lat, groundwater="unknown", last_flush_days=None, ec_class=None) -> dict:
    window = series[-90:]
    et0 = sum(row_et0(r, lat) for r in window)
    rain = sum(r["PRECTOTCORR"] or 0.0 for r in window)
    ratio = rain / et0 if et0 > 0 else 1.0

    f = []
    if ratio < 0.1:   f.append(("factor_arid", 35))
    elif ratio < 0.3: f.append(("factor_arid", 25))
    elif ratio < 0.6: f.append(("factor_arid", 12))

    f.append(("factor_gw", {"shallow": 30, "medium": 15, "unknown": 15, "deep": 0}.get(groundwater, 15)))

    if last_flush_days is None:     f.append(("factor_flush", 15))
    elif last_flush_days > 365:     f.append(("factor_flush", 20))
    elif last_flush_days > 180:     f.append(("factor_flush", 10))

    f.append(("factor_ec", {"high": 30, "medium": 15}.get((ec_class or "").lower(), 0)))

    factors = [{"key": k, "points": p} for k, p in f if p > 0]
    score = min(100, sum(x["points"] for x in factors))
    level = "LOW" if score < val("salt_med_cut") else "MEDIUM" if score < val("salt_high_cut") else "HIGH"
    return {"score": score, "level": level, "factors": sorted(factors, key=lambda x: -x["points"]),
            "rain_to_et0_ratio": round(ratio, 2)}
