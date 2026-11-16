"""Season outlook + rotation ideas built from PAST NASA POWER data (1-2 years of daily history).

This is a climatology ("what usually happens in these months at this location"), NOT a forecast.
Thresholds are placeholders that must be reviewed by the agronomist."""
import datetime as dt

from .crops import CROPS, WATER_DEMAND, recommend
from .et import row_et0
from .salinity import salinity_risk

from ..rules import val

FROST_SHARE = val("plan_frost_share")   # share of days with Tmin < -2 C above which a month counts as frosty  (app/rules.json)
PEAK_ET = val("plan_peak_et_mm")        # mm/day
COOL_ET = val("plan_cool_et_mm")        # mm/day


def monthly_climate(series: list[dict], lat: float) -> dict:
    acc: dict = {}
    for r in series:
        a = acc.setdefault(r["date"].month, {"days": 0, "rain": 0.0, "et0": 0.0, "frost": 0})
        a["days"] += 1
        a["rain"] += r["PRECTOTCORR"] or 0.0
        a["et0"] += row_et0(r, lat)
        a["frost"] += 1 if r["T2M_MIN"] < -2 else 0
    out = {}
    for m, a in acc.items():
        if a["days"] < 15:          # too little data for this month
            continue
        out[m] = {"rain_mm": round(a["rain"] / a["days"] * 30.4), "et0_day": round(a["et0"] / a["days"], 1),
                  "frost_share": a["frost"] / a["days"], "days": a["days"]}
    return out


def rain_trend(series: list[dict]) -> dict | None:
    """Last 90 days of rain vs the same 90 days one year earlier."""
    if len(series) < 455:
        return None
    end = series[-1]["date"]
    cur_lo, prev_hi = end - dt.timedelta(days=90), end - dt.timedelta(days=365)
    prev_lo = prev_hi - dt.timedelta(days=90)
    cur = sum(r["PRECTOTCORR"] or 0.0 for r in series if r["date"] > cur_lo)
    prev = sum(r["PRECTOTCORR"] or 0.0 for r in series if prev_lo < r["date"] <= prev_hi)
    if prev < 10 and cur < 10:
        return {"key": "plan_trend_same", "params": {}}
    ratio = cur / prev if prev > 0 else 2.0
    if ratio < 0.75:
        return {"key": "plan_trend_dry", "params": {"cur": round(cur), "prev": round(prev)}}
    if ratio > 1.25:
        return {"key": "plan_trend_wet", "params": {"cur": round(cur), "prev": round(prev)}}
    return {"key": "plan_trend_same", "params": {}}


def month_outlook(clim: dict, level: str, drainage: str) -> str:
    if clim["frost_share"] > FROST_SHARE:
        return "plan_frost"
    if clim["et0_day"] >= PEAK_ET:
        return "plan_peak_et_salt" if level != "LOW" else "plan_peak_et"
    if level != "LOW" and drainage == "poor":
        return "plan_drainage_first"
    if level != "LOW" and clim["et0_day"] < COOL_ET:
        return "plan_leach" if drainage == "good" else "plan_leach_check"
    return "plan_mild"


def rotation_plan(current: str, level: str, ec_class: str | None = None, water: str = "normal",
                  prefs: tuple = (), ece: float | None = None) -> list[dict]:
    """3-step idea: tolerant crop -> leaching (or a second crop when salt risk is low) -> moderate crop."""
    rec = recommend(level, ec_class, ece)
    ranked = [c for c in rec["crops"] if c["crop"] != current]
    if water == "scarce":                       # farmer priority: little irrigation water -> leave out thirsty crops
        ranked = [c for c in ranked if WATER_DEMAND[c["crop"]] != "high"] or ranked
    elif water == "limited":                    # ... or just rank them lower
        ranked.sort(key=lambda c: WATER_DEMAND[c["crop"]] == "high")
    ranked.sort(key=lambda c: c["crop"] not in prefs)       # stable: preferred crops first within the same order
    good = [c["crop"] for c in ranked if c["fit"] == "good"]
    marginal = [c["crop"] for c in ranked if c["fit"] == "marginal"]
    s1 = (good or marginal or [current])[0]
    pool = [c for c in good + marginal if c != s1]          # already ordered best-tolerance first
    if rec["level"] == "LOW":
        s2 = {"kind": "crop", "crop": pool[0] if pool else s1}
        s3 = pool[1] if len(pool) > 1 else s1
    else:
        s2 = {"kind": "leach"}
        s3 = pool[0] if pool else current
    return [{"kind": "crop", "crop": s1}, s2, {"kind": "crop", "crop": s3}]


def build_plan(series: list[dict], lat: float, crop: str = "cotton", groundwater: str = "unknown",
               drainage: str = "unknown", last_flush_days=None, ec_class=None,
               today: dt.date | None = None, months: int = 6, water: str = "normal", prefs: tuple = (), ece: float | None = None) -> dict:
    today = today or dt.date.today()
    sal = salinity_risk(series, lat, groundwater, last_flush_days, ec_class)
    level = recommend(sal["level"], ec_class, ece)["level"]
    clim = monthly_climate(series, lat)
    outlook = []
    for i in range(1, months + 1):
        m = (today.month - 1 + i) % 12 + 1
        if m in clim:
            c = clim[m]
            outlook.append({"month": m, "key": month_outlook(c, level, drainage),
                            "params": {"et0": c["et0_day"], "rain": c["rain_mm"]}})
    return {"level": level, "score": sal["score"], "outlook": outlook, "trend": rain_trend(series),
            "rotation": rotation_plan(crop, level, ec_class, water, tuple(prefs), ece),
            "history_days": len(series), "first_date": series[0]["date"].isoformat() if series else None}
