# 3-minute demo script (Sho'r Radar)

Open on your phone, inside Telegram. Record this as the backup video BEFORE the presentation.

**0:00 Problem (20 s)** "About 47% of Uzbekistan's irrigated land is salt-affected (Frontiers in Sustainable Food Systems, 2025). Farmers decide when to irrigate, when to flush salts and what to plant, usually without simple local-language advice."

**0:20 Open the app (15 s)** @ShorRadarBot -> Open app. Show the language choice (Uzbek / Russian / English). Say: "No install, it lives inside Telegram."

**0:35 Home, district view (40 s)** Tap the pilot district Nukus.
- The verdict (IRRIGATE / MONITOR / WAIT) and its three facts.
- "Latest NASA data" date and the Refresh button. Say what NASA POWER measures.
- Open **How was this decided?**: the exact rules, the farmer's values, which rule decided. "Every threshold is in one table, and it says *not yet validated by an agronomist*."

**1:15 Map (20 s)** Pilot districts coloured by signal. Switch to NASA true colour, add the vegetation layer. "This layer is visual support. It does not measure salt."

**1:35 A real field (40 s)** Add a field: type the measured ECe and the irrigation-water EC. Show the salt card: "measured" instead of "estimate". Open **Crops**: salt-tolerance cards, tap "Scarce water" and a preferred crop, watch the cards and the rotation change. Log "Irrigated" and show the signal hold ("satellites cannot see irrigation water").

**2:15 Honesty (25 s)** About -> Limitations: 50 km grid, no direct salt measurement, rules illustrative. Show docs/VALIDATION.md: "We replayed the rules on real NASA data for dry and wet periods. It checks the logic. It is not field validation, and we claim no accuracy."

**2:40 Next (20 s)** Agronomist review of thresholds, field soil-moisture data from pilot farms, SMAP at 9 km, NDVI per field.

## Before you present
- `python -m scripts.precache` with internet (NASA data copy on disk).
- `python -m scripts.run_all`, open the app once, check the menu button works.
- Charge the phone, turn off sleep on the laptop, have the recorded video ready.
