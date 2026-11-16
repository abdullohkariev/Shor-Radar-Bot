"""Reference evapotranspiration (ET0) by Hargreaves-Samani, using only temperature + latitude.
Ra (extraterrestrial radiation) is computed as in FAO-56 eq. 21."""
import math


def extraterrestrial_radiation(lat_deg: float, doy: int) -> float:
    """Ra in mm/day equivalent evaporation."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    delta = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    ws = math.acos(x)
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return ra * 0.408


def hargreaves_et0(tmax: float, tmin: float, lat: float, doy: int) -> float:
    tmean = (tmax + tmin) / 2
    return max(0.0, 0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0))
               * extraterrestrial_radiation(lat, doy))


def row_et0(row: dict, lat: float) -> float:
    return hargreaves_et0(row["T2M_MAX"], row["T2M_MIN"], lat, row["date"].timetuple().tm_yday)
