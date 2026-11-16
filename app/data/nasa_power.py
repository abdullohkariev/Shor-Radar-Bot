"""NASA POWER daily point data (MERRA-2 / CERES based), community AG.

Three layers of resilience so a slow or unreachable NASA server does not break the app:
1) in-memory cache (6 h), 2) retries, 3) a copy on disk (cache/) that survives restarts and is served, marked stale,
when NASA cannot be reached. `scripts/precache.py` fills the disk copy for all covered areas before a demo."""
import asyncio
import datetime as dt
import json
import pathlib
import time

import httpx

from .. import config
from ..config import POWER_URL, POWER_CACHE_TTL

PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M",
          "ALLSKY_SFC_SW_DWN", "GWETROOT", "GWETTOP"]
_CACHE: dict = {}
# What the app shows in its dataset log: the API version NASA reported and when we last got fresh data.
META = {"api_name": "NASA POWER Daily API", "api_version": None, "accessed": None, "stale_used": False}


def _cell(lat, lon):
    # POWER meteorology is on a ~0.5 degree grid; cache per cell.
    return (round(lat * 2) / 2, round(lon * 2) / 2)


def parse_power(data: dict) -> list[dict]:
    """Turn POWER's {param: {YYYYMMDD: value}} into a sorted list of daily rows.
    POWER uses -999 for missing values."""
    rows = []
    for d in sorted(data["T2M"].keys()):
        row = {"date": dt.datetime.strptime(d, "%Y%m%d").date()}
        for p in PARAMS:
            v = data.get(p, {}).get(d)
            row[p] = None if v is None or v <= -990 else float(v)
        if row["T2M_MAX"] is not None and row["T2M_MIN"] is not None:
            rows.append(row)
    return rows


def invalidate(lat: float, lon: float):
    for k in [k for k in _CACHE if k[:2] == _cell(lat, lon)]:
        _CACHE.pop(k, None)


# ---------- copy on disk (survives restarts, served marked stale when NASA is unreachable) ----------
def _disk_path(key) -> pathlib.Path:
    return pathlib.Path(config.CACHE_DIR) / f"power_{key[0]}_{key[1]}_{key[2]}.json"


def _save_disk(key, rows):
    try:
        payload = json.dumps({"saved": time.time(), "api_version": META["api_version"],
                              "rows": [{**r, "date": r["date"].isoformat()} for r in rows]})
        p = _disk_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload, encoding="utf-8")
    except Exception:
        pass                                           # the stored copy is a convenience, never a reason to fail


def _load_disk(key):
    try:
        raw = _disk_path(key).read_text(encoding="utf-8")
        d = json.loads(raw)
        return [{**r, "date": dt.date.fromisoformat(r["date"])} for r in d["rows"]], d["saved"]
    except Exception:
        return None


async def fetch_power(lat: float, lon: float, days: int = 90, client=None, force: bool = False) -> list[dict]:
    """`force=True` skips every cache and asks NASA."""
    key = _cell(lat, lon) + (days,)
    hit = _CACHE.get(key)
    if not force and hit and time.time() - hit[0] < POWER_CACHE_TTL:
        return hit[1]
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    params = {
        "parameters": ",".join(PARAMS), "community": "AG",
        "latitude": lat, "longitude": lon,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    own = client is None
    client = client or httpx.AsyncClient(timeout=40)
    last_err = None
    try:
        for attempt in range(3):                       # NASA is sometimes slow: retry with a short pause
            try:
                r = await client.get(POWER_URL, params=params)
                r.raise_for_status()
                body = r.json()
                rows = parse_power(body["properties"]["parameter"])
                META["api_version"] = (body.get("header") or {}).get("api", {}).get("version") or META["api_version"]
                META["accessed"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                META["stale_used"] = False
                _CACHE[key] = (time.time(), rows)
                _save_disk(key, rows)
                return rows
            except Exception as e:
                last_err = e
                await asyncio.sleep(1.5 * (attempt + 1))
    finally:
        if own:
            await client.aclose()
    if hit:                                            # still failing: serve the last good data (stale) rather than an error
        META["stale_used"] = True
        return hit[1]
    disk = _load_disk(key)
    if disk:
        META["stale_used"] = True
        _CACHE[key] = (time.time() - POWER_CACHE_TTL + 300, disk[0])     # retry NASA again in ~5 minutes
        return disk[0]
    raise last_err
