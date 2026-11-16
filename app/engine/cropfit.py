"""Crop cards for the Crops tab: salt fit (FAO reference thresholds) + the farmer's own priorities
(water availability, preferred crops). Reference values only, never a planting instruction."""
from .crops import WATER_DEMAND, recommend

FIT_ORDER = {"good": 0, "marginal": 1, "avoid": 2}


def crop_cards(level: str, ec_class: str | None = None, water: str = "normal", prefs=(), current: str | None = None,
               ece: float | None = None) -> dict:
    rec = recommend(level, ec_class, ece)
    cards = []
    for c in rec["crops"]:
        wd = WATER_DEMAND[c["crop"]]
        notes = []
        if wd == "high" and water in ("limited", "scarce"):
            notes.append("water_" + water)
        cards.append({**c, "water_demand": wd, "preferred": c["crop"] in prefs, "current": c["crop"] == current, "notes": notes})
    cards.sort(key=lambda x: (FIT_ORDER[x["fit"]], not x["preferred"], -x["threshold"]))
    return {"level": rec["level"], "assumed_ec": rec["assumed_ec"], "rotation_key": rec["rotation_key"], "crops": cards}
