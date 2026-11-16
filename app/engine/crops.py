"""Crop reference data.

!! PLACEHOLDER VALUES - must be reviewed against FAO-56 (Kc) and FAO Irrigation & Drainage
!! Paper 29 / Maas & Hoffman 1977 (salinity thresholds) by Yasmin / an agronomist.
ec_threshold = soil salinity ECe (dS/m) up to which yield is not reduced.
"""

STAGES = ["fallow", "initial", "development", "mid", "late"]

CROPS = {
    "cotton":     {"kc": {"initial": 0.35, "development": 0.75, "mid": 1.15, "late": 0.70}, "ec_threshold": 7.7},
    "wheat":      {"kc": {"initial": 0.40, "development": 0.80, "mid": 1.15, "late": 0.40}, "ec_threshold": 6.0},
    "barley":     {"kc": {"initial": 0.30, "development": 0.75, "mid": 1.15, "late": 0.25}, "ec_threshold": 8.0},
    "sugar_beet": {"kc": {"initial": 0.35, "development": 0.80, "mid": 1.20, "late": 0.70}, "ec_threshold": 7.0},
    "sorghum":    {"kc": {"initial": 0.30, "development": 0.75, "mid": 1.00, "late": 0.55}, "ec_threshold": 6.8},
    "rice":       {"kc": {"initial": 1.05, "development": 1.10, "mid": 1.20, "late": 0.90}, "ec_threshold": 3.0},
    "tomato":     {"kc": {"initial": 0.60, "development": 0.90, "mid": 1.15, "late": 0.80}, "ec_threshold": 2.5},
    "alfalfa":    {"kc": {"initial": 0.40, "development": 0.80, "mid": 1.20, "late": 1.10}, "ec_threshold": 2.0},
    "maize":      {"kc": {"initial": 0.30, "development": 0.80, "mid": 1.20, "late": 0.60}, "ec_threshold": 1.7},
    "potato":     {"kc": {"initial": 0.50, "development": 0.80, "mid": 1.15, "late": 0.75}, "ec_threshold": 1.7},
    "onion":      {"kc": {"initial": 0.70, "development": 0.90, "mid": 1.05, "late": 0.75}, "ec_threshold": 1.2},
}

# Irrigation thresholds (placeholders, same for all crops for now)
from ..rules import val

DRY_WETNESS = val("dry_wetness")        # GWETROOT below this -> irrigate        (app/rules.json)
WATCH_WETNESS = val("watch_wetness")    # below this -> monitor
MAX_DEFICIT_MM = float(val("max_deficit_mm"))   # 7-day crop-ET minus effective rain

LEVELS = ["LOW", "MEDIUM", "HIGH"]
EC_ESTIMATE = {"LOW": 1.5, "MEDIUM": 4.0, "HIGH": 7.0}   # assumed ECe for each risk level


def tolerance_class(thr: float) -> str:
    return "tolerant" if thr >= 6 else "moderate" if thr >= 3 else "sensitive"


def class_from_ece(ece: float) -> str:
    """FAO-style class of a MEASURED soil ECe (dS/m): low < 4 <= medium < 8 <= high."""
    return "high" if ece >= val("ece_high") else "medium" if ece >= val("ece_med") else "low"


def recommend(level: str, ec_class: str | None = None, ece: float | None = None) -> dict:
    """Rank crops for the salt level. A MEASURED ECe decides the level and is used as the number;
    otherwise a farmer-reported class can only raise the weather-based risk level."""
    if ece is not None:
        level = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}[class_from_ece(ece)]
        est = float(ece)
    else:
        user_level = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}.get((ec_class or "").lower())
        if user_level and LEVELS.index(user_level) > LEVELS.index(level):
            level = user_level
        est = EC_ESTIMATE[level]
    out = []
    for name, c in CROPS.items():
        thr = c["ec_threshold"]
        fit = "good" if thr >= est else "marginal" if thr >= est * 0.6 else "avoid"
        out.append({"crop": name, "threshold": thr, "tolerance": tolerance_class(thr), "fit": fit})
    order = {"good": 0, "marginal": 1, "avoid": 2}
    out.sort(key=lambda x: (order[x["fit"]], -x["threshold"]))
    return {"level": level, "assumed_ec": est, "crops": out,
            "rotation_key": {"LOW": "rot_low", "MEDIUM": "rot_medium", "HIGH": "rot_high"}[level]}


# !! PLACEHOLDER (review with the agronomist): rough irrigation-water demand class per crop.
WATER_DEMAND = {"cotton": "high", "wheat": "medium", "barley": "low", "sugar_beet": "high", "sorghum": "low",
                "rice": "high", "tomato": "medium", "alfalfa": "high", "maize": "medium", "potato": "medium", "onion": "medium"}
