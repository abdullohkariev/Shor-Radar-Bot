"""Run this FIRST on a machine with internet:  python -m scripts.check_apis
Confirms NASA POWER + Open-Meteo respond, and prints what we get for Urgench, Khorezm."""
import asyncio
import time

from app.data.forecast import fetch_forecast
from app.data.nasa_power import fetch_power


async def main():
    lat, lon = 41.55, 60.63
    t = time.time()
    rows = await fetch_power(lat, lon, days=30)
    print(f"POWER: {len(rows)} days in {time.time() - t:.1f}s; last row:")
    print(rows[-1])
    print("GWETROOT available:", sum(r['GWETROOT'] is not None for r in rows), "/", len(rows))
    fc = await fetch_forecast(lat, lon)
    print("Open-Meteo:", "unreachable" if fc is None else f"{len(fc)} days; first: {fc[0]}")

asyncio.run(main())
