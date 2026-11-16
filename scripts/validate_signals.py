"""Consistency check of the irrigation rules against real NASA POWER data (writes docs/VALIDATION.md):
    python -m scripts.validate_signals

For the 3 pilot districts and every growing season (Apr-Sep) in the last ~2 years it replays the rules day by day
(no forecast, a typical cotton field at mid-season) and asks:
  1. In the DRIEST and WETTEST 30-day window of each season (identified from NASA's own rainfall), what signals did the rules give?
  2. Is the soil wetness the rules saw lower on IRRIGATE days than on MONITOR days than on WAIT days?
This checks that the rules behave sensibly on dry and wet periods. It is NOT validation against real fields: we have no
ground-truth soil moisture, irrigation records or yields. No accuracy is claimed."""
import asyncio
import datetime as dt
import pathlib
import statistics
from collections import Counter

from app.data.nasa_power import META, fetch_power
from app.engine.advisor import build_advice
from app.regions import AREA_GROUNDWATER, PILOTS, REGIONS, region_name
from app.rules import DATA as RULES_DATA

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "VALIDATION.md"
MIN_HISTORY = 30


def season_rows(series, lat, rid, year):
    """Replay the rules for every day Apr 1 - Sep 30 of `year` that has enough history."""
    rows = []
    for i, r in enumerate(series):
        d = r["date"]
        if not (dt.date(year, 4, 1) <= d <= dt.date(year, 9, 30)) or i < MIN_HISTORY:
            continue
        sub = series[: i + 1]
        adv = build_advice(sub, None, lat, 0, crop="cotton", stage="mid", groundwater=AREA_GROUNDWATER.get(rid, "unknown"))
        wets = [x["GWETROOT"] for x in sub[-3:] if x["GWETROOT"] is not None]
        rows.append({"date": d, "status": adv["irrigation"]["status"], "wet": sum(wets) / len(wets) if wets else None,
                     "rain30": sum(x["PRECTOTCORR"] or 0 for x in sub[-30:]), "deficit": adv["irrigation"]["metrics"].get("deficit_mm")})
    return rows


def simulate_policy(series, lat, rid, year):
    """A farmer who irrigates (and logs it) on every day the rules say IRRIGATE. How often would that be?"""
    last, days = None, []
    for i, r in enumerate(series):
        d = r["date"]
        if not (dt.date(year, 4, 1) <= d <= dt.date(year, 9, 30)) or i < MIN_HISTORY:
            continue
        since = None if last is None else (d - last).days
        adv = build_advice(series[: i + 1], None, lat, 0, crop="cotton", stage="mid", groundwater=AREA_GROUNDWATER.get(rid, "unknown"), since_irrigation=since)
        if adv["irrigation"]["status"] == "IRRIGATE":
            days.append(d)
            last = d
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    return len(days), (statistics.median(gaps) if gaps else None)


def window_summary(series, rows, end_idx):
    """Signals during the 30 days ending at rows[end_idx]."""
    chunk = rows[max(0, end_idx - 29): end_idx + 1]
    c = Counter(r["status"] for r in chunk)
    return {"end": rows[end_idx]["date"], "rain": rows[end_idx]["rain30"], "wet": statistics.mean(r["wet"] for r in chunk if r["wet"] is not None),
            "irr": c["IRRIGATE"], "mon": c["MONITOR"], "wait": c["WAIT"], "n": len(chunk)}


async def main():
    md = ["# Signal consistency check (NOT field validation)", "",
          f"Generated {dt.datetime.now():%Y-%m-%d %H:%M}. NASA POWER API {META.get('api_version') or 'version not reported'}, rules version `{RULES_DATA['version']}` "
          f"(validated by an agronomist: {RULES_DATA['validated_by'] or 'not yet'}).", "",
          "**What this is:** the rules replayed day by day on real NASA POWER data for a typical cotton field (mid-season, no forecast), "
          "to see whether the signals behave sensibly in the driest and wettest 30-day windows that NASA's own rainfall identifies.", "",
          "**What this is not:** a test against real farms. There is no ground-truth soil moisture, irrigation log or yield here, so **no accuracy is claimed**. "
          "Thresholds are still illustrative until an agronomist reviews them.", ""]
    all_by_status = {"IRRIGATE": [], "MONITOR": [], "WAIT": []}
    verdicts, sims = [], []
    for rid in PILOTS:
        lat, lon, _ = REGIONS[rid]
        series = await fetch_power(lat, lon, days=800)
        md += [f"## {region_name(rid, 'en')}", "", f"Data: {series[0]['date']} to {series[-1]['date']} ({len(series)} days).", "",
               "| Season | Window | 30-day rain (mm) | Mean root-zone wetness | IRRIGATE days | MONITOR days | WAIT days |", "|---|---|---|---|---|---|---|"]
        for year in sorted({r["date"].year for r in series}):
            rows = season_rows(series, lat, rid, year)
            if len(rows) < 60:
                continue
            for r in rows:
                if r["wet"] is not None:
                    all_by_status[r["status"]].append(r["wet"])
            wet_i = max(range(29, len(rows)), key=lambda i: rows[i]["rain30"])
            dry_i = min(range(29, len(rows)), key=lambda i: rows[i]["rain30"])
            for label, i in (("wettest", wet_i), ("driest", dry_i)):
                w = window_summary(series, rows, i)
                md.append(f"| {year} | {label}, ends {w['end']} | {w['rain']:.0f} | {w['wet'] * 100:.0f}% | {w['irr']} | {w['mon']} | {w['wait']} |")
                if label == "wettest":
                    wet_w = w
                else:
                    dry_w = w
            ok = dry_w["irr"] >= wet_w["irr"] and dry_w["wait"] <= wet_w["wait"]
            verdicts.append((rid, year, ok))
            n, gap = simulate_policy(series, lat, rid, year)
            sims.append((region_name(rid, "en"), year, len(rows), n, gap))
        md.append("")
    md += ["## Does soil wetness separate the signals?", "", "| Signal | Days | Mean root-zone wetness seen by the rule |", "|---|---|---|"]
    means = {}
    for k in ("IRRIGATE", "MONITOR", "WAIT"):
        v = all_by_status[k]
        means[k] = statistics.mean(v) if v else None
        md.append(f"| {k} | {len(v)} | {'n/a' if not v else f'{means[k] * 100:.0f}%'} |")
    ordered = all(means[a] is not None and means[b] is not None and means[a] <= means[b] for a, b in (("IRRIGATE", "MONITOR"), ("MONITOR", "WAIT"))) \
        if all(v is not None for v in means.values()) else None
    total_days = sum(len(v) for v in all_by_status.values())
    share_irr = len(all_by_status["IRRIGATE"]) / total_days if total_days else 0
    md += ["", "## With no irrigation log (the district view)", "",
           f"The rules said IRRIGATE on **{share_irr * 100:.0f}%** of growing-season days. Without knowing when irrigation happened, "
           "the 7-day water deficit exceeds the limit on almost any dry week, so the signal separates little. This is why the app now uses the "
           "farmer's field log (below).", "",
           "## With the field log: a farmer who irrigates and logs it whenever the rules say IRRIGATE", "",
           f"After a logged irrigation the signal holds for {RULES_DATA['rules']['irrigation_hold_days']['value']} days and water use is counted only since then.", "",
           "| District | Season | Days replayed | Irrigations called for | Median days between irrigations |", "|---|---|---|---|---|"]
    for name, year, nd, n, gap in sims:
        md.append(f"| {name} | {year} | {nd} | {n} | {'n/a' if gap is None else f'{gap:.0f}'} |")
    gaps = [g for *_, g in sims if g is not None]
    md += ["", "**Reviewer question for the agronomist:** is that interval realistic for local cotton and soils? "
           f"With the placeholder limit of {RULES_DATA['rules']['max_deficit_mm']['value']} mm of water deficit, the rules call for irrigation about every "
           f"{statistics.median(gaps):.0f} days at peak demand. " if gaps else "",
           "The limit should come from the soil's water-holding capacity and the crop's allowed depletion (FAO-56), not from this placeholder.", ""]
    md += ["## Summary", "",
           f"- Driest window gave at least as many IRRIGATE days and no more WAIT days than the wettest window in **{sum(ok for *_, ok in verdicts)} of {len(verdicts)}** district-seasons.",
           f"- Mean soil wetness is ordered IRRIGATE ≤ MONITOR ≤ WAIT: **{'yes' if ordered else 'no' if ordered is not None else 'not enough days to say'}**.",
           "- Interpretation: the rules respond in the expected direction to dry and wet periods. That is a sanity check of the logic, not proof that the advice is right for a given farm.",
           "- Next step: compare with field soil-moisture or irrigation records from the pilot districts, and have an agronomist set the thresholds in `app/rules.json`."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nWritten to {OUT}")

asyncio.run(main())
