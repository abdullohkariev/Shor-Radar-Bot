"""Fill the disk copy of NASA data for every covered area, so the app still works if NASA or the venue Wi-Fi is down:
    python -m scripts.precache
Run it with internet before a demo (takes ~1-2 minutes). The data is stored in cache/ and served, marked stale, only when NASA cannot be reached."""
import asyncio

from app.data.forecast import fetch_forecast
from app.data.nasa_power import META, fetch_power
from app.regions import REGIONS


async def main():
    ok = bad = 0
    for rid, (lat, lon, names) in REGIONS.items():
        for days in (90, 730):
            try:
                rows = await fetch_power(lat, lon, days=days)
                ok += 1
                print(f"{rid:10} {days:4} days: {len(rows)} rows, latest {rows[-1]['date']}")
            except Exception as e:
                bad += 1
                print(f"{rid:10} {days:4} days: FAILED ({e})")
        await fetch_forecast(lat, lon)
    print(f"\nDone: {ok} ok, {bad} failed. NASA POWER API version: {META['api_version']}")

asyncio.run(main())
