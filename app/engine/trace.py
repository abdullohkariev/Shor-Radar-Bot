"""Explains an irrigation decision: which rules were checked, with the farmer's own numbers, and which one decided.
The rule order mirrors engine/irrigation.py exactly; thresholds come from app/rules.json."""
from ..rules import RULES, val


def irrigation_trace(metrics: dict, status: str, lang: str = "en") -> dict | None:
    if not metrics:                                     # fallow field: no rules were evaluated
        return None
    wet, deficit, rain3 = metrics.get("root_wetness"), metrics.get("deficit_mm"), metrics.get("rain_next3d_mm")
    rows = []

    def row(rid, value, op, threshold, hit, outcome, unit=None):
        rows.append({"id": rid, "label": RULES[rid]["label"].get(lang, RULES[rid]["label"]["en"]), "value": value, "op": op,
                     "threshold": threshold, "unit": unit or RULES[rid]["unit"], "hit": bool(hit), "outcome": outcome})

    since = metrics.get("days_since_irrigation")
    if since is not None:
        row("irrigation_hold_days", since, "<=", val("irrigation_hold_days"), since <= val("irrigation_hold_days"), "WAIT")
    if metrics.get("forecast_available"):
        row("wait_rain_mm", rain3, ">=", val("wait_rain_mm"), rain3 >= val("wait_rain_mm"), "WAIT")
    if wet is not None:
        row("dry_wetness", wet, "<", val("dry_wetness"), wet < val("dry_wetness"), "IRRIGATE")
    row("max_deficit_mm", deficit, ">", val("max_deficit_mm"), deficit > val("max_deficit_mm"), "IRRIGATE")
    if wet is not None:
        row("watch_wetness", wet, "<", val("watch_wetness"), wet < val("watch_wetness"), "MONITOR")
    lim = val("watch_deficit_frac") * val("max_deficit_mm")
    row("watch_deficit_frac", deficit, ">", round(lim, 1), deficit > lim, "MONITOR", unit="mm")
    decisive = next((i for i, r in enumerate(rows) if r["hit"]), None)
    return {"rows": rows, "decisive": decisive, "outcome": status}
