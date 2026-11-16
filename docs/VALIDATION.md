# Signal consistency check (NOT field validation)

Generated 2026-11-14 21:43. NASA POWER API version not reported, rules version `0.2-illustrative` (validated by an agronomist: not yet).

**What this is:** the rules replayed day by day on real NASA POWER data for a typical cotton field (mid-season, no forecast), to see whether the signals behave sensibly in the driest and wettest 30-day windows that NASA's own rainfall identifies.

**What this is not:** a test against real farms. There is no ground-truth soil moisture, irrigation log or yield here, so **no accuracy is claimed**. Thresholds are still illustrative until an agronomist reviews them.

## Nukus (Karakalpakstan)

Data: 2024-09-05 to 2026-11-11 (798 days).

| Season | Window | 30-day rain (mm) | Mean root-zone wetness | IRRIGATE days | MONITOR days | WAIT days |
|---|---|---|---|---|---|---|
| 2025 | wettest, ends 2025-06-10 | 16 | 48% | 30 | 0 | 0 |
| 2025 | driest, ends 2025-07-10 | 0 | 47% | 30 | 0 | 0 |
| 2026 | wettest, ends 2026-04-30 | 39 | 52% | 14 | 13 | 3 |
| 2026 | driest, ends 2026-08-20 | 0 | 47% | 30 | 0 | 0 |

## Gulistan (Syrdarya)

Data: 2024-09-05 to 2026-11-11 (798 days).

| Season | Window | 30-day rain (mm) | Mean root-zone wetness | IRRIGATE days | MONITOR days | WAIT days |
|---|---|---|---|---|---|---|
| 2025 | wettest, ends 2025-05-02 | 20 | 58% | 27 | 3 | 0 |
| 2025 | driest, ends 2025-07-20 | 0 | 43% | 30 | 0 | 0 |
| 2026 | wettest, ends 2026-05-21 | 61 | 58% | 28 | 2 | 0 |
| 2026 | driest, ends 2026-08-23 | 0 | 43% | 30 | 0 | 0 |

## Bukhara

Data: 2024-09-05 to 2026-11-11 (798 days).

| Season | Window | 30-day rain (mm) | Mean root-zone wetness | IRRIGATE days | MONITOR days | WAIT days |
|---|---|---|---|---|---|---|
| 2025 | wettest, ends 2025-04-30 | 16 | 44% | 25 | 5 | 0 |
| 2025 | driest, ends 2025-06-08 | 0 | 42% | 30 | 0 | 0 |
| 2026 | wettest, ends 2026-05-02 | 37 | 45% | 24 | 6 | 0 |
| 2026 | driest, ends 2026-07-29 | 0 | 42% | 30 | 0 | 0 |

## Does soil wetness separate the signals?

| Signal | Days | Mean root-zone wetness seen by the rule |
|---|---|---|
| IRRIGATE | 1053 | 46% |
| MONITOR | 40 | 54% |
| WAIT | 5 | 57% |

## With no irrigation log (the district view)

The rules said IRRIGATE on **96%** of growing-season days. Without knowing when irrigation happened, the 7-day water deficit exceeds the limit on almost any dry week, so the signal separates little. This is why the app now uses the farmer's field log (below).

## With the field log: a farmer who irrigates and logs it whenever the rules say IRRIGATE

After a logged irrigation the signal holds for 4 days and water use is counted only since then.

| District | Season | Days replayed | Irrigations called for | Median days between irrigations |
|---|---|---|---|---|
| Nukus (Karakalpakstan) | 2025 | 183 | 34 | 5 |
| Nukus (Karakalpakstan) | 2026 | 183 | 33 | 5 |
| Gulistan (Syrdarya) | 2025 | 183 | 35 | 5 |
| Gulistan (Syrdarya) | 2026 | 183 | 34 | 5 |
| Bukhara | 2025 | 183 | 36 | 5 |
| Bukhara | 2026 | 183 | 35 | 5 |

**Reviewer question for the agronomist:** is that interval realistic for local cotton and soils? With the placeholder limit of 25 mm of water deficit, the rules call for irrigation about every 5 days at peak demand. 
The limit should come from the soil's water-holding capacity and the crop's allowed depletion (FAO-56), not from this placeholder.

## Summary

- Driest window gave at least as many IRRIGATE days and no more WAIT days than the wettest window in **6 of 6** district-seasons.
- Mean soil wetness is ordered IRRIGATE ≤ MONITOR ≤ WAIT: **yes**.
- Interpretation: the rules respond in the expected direction to dry and wet periods. That is a sanity check of the logic, not proof that the advice is right for a given farm.
- Next step: compare with field soil-moisture or irrigation records from the pilot districts, and have an agronomist set the thresholds in `app/rules.json`.
