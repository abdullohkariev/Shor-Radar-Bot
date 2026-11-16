"""Covered locations (pilot + main farming areas). Coordinates are approximate city centres.
!! Team: confirm the final 3 pilot districts and verify coordinates on a map."""
import math

# id: (lat, lon, {en, uz, ru})
REGIONS = {
    "nukus":     (42.46, 59.61, {"en": "Nukus (Karakalpakstan)", "uz": "Nukus (Qoraqalpog'iston)", "ru": "Нукус (Каракалпакстан)"}),
    "urgench":   (41.55, 60.63, {"en": "Urgench (Khorezm)", "uz": "Urganch (Xorazm)", "ru": "Ургенч (Хорезм)"}),
    "khiva":     (41.38, 60.36, {"en": "Khiva (Khorezm)", "uz": "Xiva (Xorazm)", "ru": "Хива (Хорезм)"}),
    "bukhara":   (39.77, 64.42, {"en": "Bukhara", "uz": "Buxoro", "ru": "Бухара"}),
    "navoi":     (40.10, 65.37, {"en": "Navoi", "uz": "Navoiy", "ru": "Навои"}),
    "samarkand": (39.65, 66.96, {"en": "Samarkand", "uz": "Samarqand", "ru": "Самарканд"}),
    "qarshi":    (38.86, 65.79, {"en": "Qarshi (Kashkadarya)", "uz": "Qarshi (Qashqadaryo)", "ru": "Карши (Кашкадарья)"}),
    "termez":    (37.22, 67.28, {"en": "Termez (Surkhandarya)", "uz": "Termiz (Surxondaryo)", "ru": "Термез (Сурхандарья)"}),
    "jizzakh":   (40.12, 67.84, {"en": "Jizzakh", "uz": "Jizzax", "ru": "Джизак"}),
    "gulistan":  (40.49, 68.78, {"en": "Gulistan (Syrdarya)", "uz": "Guliston (Sirdaryo)", "ru": "Гулистан (Сырдарья)"}),
    "tashkent":  (41.31, 69.28, {"en": "Tashkent", "uz": "Toshkent", "ru": "Ташкент"}),
    "andijan":   (40.78, 72.34, {"en": "Andijan", "uz": "Andijon", "ru": "Андижан"}),
    "namangan":  (41.00, 71.67, {"en": "Namangan", "uz": "Namangan", "ru": "Наманган"}),
    "fergana":   (40.38, 71.78, {"en": "Fergana", "uz": "Farg'ona", "ru": "Фергана"}),
}

# Same bounding box the API uses; NASA POWER is global but our rules are tuned for Uzbekistan.
LAT_RANGE = (37.0, 46.0)
LON_RANGE = (55.0, 74.0)


def covered(lat: float, lon: float) -> bool:
    return LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]


def region_name(rid: str | None, lang: str = "en") -> str:
    r = REGIONS.get(rid or "")
    return r[2].get(lang, r[2]["en"]) if r else "-"


def nearest_region(lat: float, lon: float) -> str:
    def dist(r):
        dlat = math.radians(r[0] - lat)
        dlon = math.radians(r[1] - lon) * math.cos(math.radians(lat))
        return dlat * dlat + dlon * dlon
    return min(REGIONS, key=lambda k: dist(REGIONS[k]))


PILOTS = ["nukus", "gulistan", "bukhara"]        # !! confirm the final 3 pilot districts

# !! PLACEHOLDER defaults used for a district-level view when the farmer has not entered a field.
AREA_GROUNDWATER = {"nukus": "shallow", "urgench": "shallow", "khiva": "shallow", "gulistan": "shallow",
                    "bukhara": "medium", "navoi": "medium", "jizzakh": "medium", "fergana": "deep"}

# Published regional statistics (share of irrigated land affected by salinization).
# Source: Frontiers in Sustainable Food Systems (2025). NOT a measurement of any individual field.
REGION_SALINITY = {"nukus": ("Karakalpakstan", 79.1), "gulistan": ("Syrdarya", 82.3),
                   "bukhara": ("Bukhara", 75.1), "jizzakh": ("Jizzakh", 72.1)}
