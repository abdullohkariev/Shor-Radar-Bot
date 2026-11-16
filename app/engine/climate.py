"""Plain numbers for the dashboard: latest NASA POWER values, 7/30-day rain, trend series, forecast strip."""
from .et import row_et0


def _last(series, key):
    """Latest non-missing value and its date (POWER's newest days can be empty while the data is still processed)."""
    for r in reversed(series):
        if r.get(key) is not None:
            return r[key], r["date"].isoformat()
    return None, None


def _r(v, n=1):
    return None if v is None else round(v, n)


def climate_block(series: list[dict], forecast, lat: float, days: int = 90) -> dict:
    t, t_date = _last(series, "T2M")
    tmax, _ = _last(series, "T2M_MAX")
    tmin, _ = _last(series, "T2M_MIN")
    rh, _ = _last(series, "RH2M")
    wr, wr_date = _last(series, "GWETROOT")
    wt, _ = _last(series, "GWETTOP")
    last7 = series[-7:]
    et0 = sum(row_et0(r, lat) for r in last7) / max(len(last7), 1)
    chart = [{"d": r["date"].isoformat(), "t": _r(r["T2M"]), "p": _r(r["PRECTOTCORR"] or 0.0), "wr": _r(r["GWETROOT"], 3),
              "wt": _r(r["GWETTOP"], 3), "rh": _r(r["RH2M"], 0)} for r in series[-days:]]
    return {
        "latest": {"temp": _r(t), "tmax": _r(tmax), "tmin": _r(tmin), "humidity": _r(rh, 0),
                   "soil_root": _r(wr, 2), "soil_top": _r(wt, 2), "et0": _r(et0)},
        "rain_7d": _r(sum(r["PRECTOTCORR"] or 0.0 for r in series[-7:])),
        "rain_30d": _r(sum(r["PRECTOTCORR"] or 0.0 for r in series[-30:])),
        "data_date": series[-1]["date"].isoformat() if series else None,
        "soil_date": wr_date or t_date,
        "chart": chart,
        "forecast": [{"d": f["date"].isoformat(), "rain": _r(f["rain"]), "tmax": _r(f["tmax"]), "tmin": _r(f["tmin"])}
                     for f in (forecast or [])[:7]],
    }
