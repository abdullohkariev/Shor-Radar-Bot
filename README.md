# Sho'r Radar (NASA Space Apps 2026, CST team)

Decision support for farmers in Uzbekistan: **irrigate / monitor / wait**, a **salt-risk indicator**,
**qualified flush-timing guidance**, and **salt-aware crop suggestions**, in Uzbek, Russian and English.
Delivered as a Telegram bot plus a Mini App with a map dashboard, running from a laptop.

> Decision support, not a measurement. Salt is not observed directly: we score conditions that favour build-up.

## Runs on your laptop only
Everything runs on one Windows laptop: no cloud, no hosting account. The bot works while the laptop is on and online.
One-time setup (PowerShell):
```powershell
pip install -r requirements.txt
winget install --id Cloudflare.cloudflared      # free HTTPS tunnel for the Mini App; reopen the terminal afterwards
copy .env.example .env                          # then put your BotFather token into .env
python -m pytest -q                             # offline tests (incl. a simulated bot conversation)
```
Start the bot (every time):
```powershell
python -m scripts.run_all
```
This starts the web server (Mini App + map), a free Cloudflare tunnel that gives it a public HTTPS address (Telegram requires
HTTPS), and the Telegram bot, and sets the bot's menu button to that address. The address changes on every run and the bot
re-registers it by itself; a watchdog restarts the tunnel or server if they die. Ctrl+C stops everything. While the laptop is
off or asleep the bot does not answer. Data lives in `shor_radar.db` (SQLite) and `cache/` (NASA data) next to the code.

Other commands: `python -m scripts.check_apis` (confirm NASA POWER + Open-Meteo are reachable), `python -m scripts.precache`
(fill the NASA disk copy before a demo), `python -m app.bot` (bot only, no Mini App address), `uvicorn app.main:app` (web only).
Set `SHOR_DEMO=1` to run on synthetic data when NASA is unreachable (messages are labelled "demo data").
The marketing website is a separate project (static page on GitHub Pages) and is not part of this repository.

## Telegram Mini App (opens inside Telegram like an app)
`app/static/app.html` + `app/webapp_api.py`, served at `/app`; `app/static/index.html` is the map page opened by `/map`.
In Telegram: open the bot -> blue **Sho'r Radar** button next to the message box (or `/app`, or the 🚀 button in the menu).
Security: every API call carries Telegram's signed `initData`, verified with the bot token; users can only touch their own data.

## Mini App screens (app/static/app.html)
Home (verdict, NASA conditions + date of latest data, refresh, soil-wetness gauge, 7-day forecast, 30/90-day trends, salt risk, flush hint, field log) ·
Map (pilot districts + your fields coloured by signal; OSM / satellite / NASA GIBS true-colour; MODIS NDVI overlay) ·
Crops (FAO salt tolerance cards, farmer priorities: water availability + preferred crops, 3-step rotation with reasons, 6-month outlook) ·
Community · About (how it works, data sources, limitations, validation status). Settings in the gear icon.
Brand colours come from the logo: ink #0E2A2E, green #2EA05A, amber #F2B01E, red #DA3A2C, wordmark green #1D7A45. Logo files: app/static/img/.
All Mini App text lives in `app/appstrings.py` (+ `ui.py`, `messages.py`); `tests/test_app_strings.py` fails if a key is missing in any language.

## Rules, honesty and resilience
- **All thresholds** live in `app/rules.json` (versioned, labelled `placeholder` until an agronomist reviews them, `validated_by` is empty). The app shows them (About -> Rules & thresholds) and explains each decision (Home -> How was this decided?).
- **Measured salinity**: farmers enter ECe (dS/m, with date) and irrigation-water EC; a measurement decides the salt level and crop fit. Without one the app says "field salinity not measured".
- **Field log**: logging an irrigation holds the signal and resets the water deficit; logging a flush updates days since flushing.
- **Alerts**: frost and heavy-rain warnings plus the normal advice, at the hour each farmer picks (Settings).
- **Outages**: NASA data is kept on disk (`cache/`) and served, marked stale, if NASA is unreachable; the page falls back to the last data saved on the phone. `python -m scripts.precache` fills the disk copy for all areas before a demo.
- **Consistency check**: `python -m scripts.validate_signals` writes `docs/VALIDATION.md` (real NASA data, dry vs wet periods). It is NOT field validation.
- **Verified agronomist badge** in the community: `python -m scripts.set_role <telegram_id> agronomist`.
- Demo story: `docs/DEMO_SCRIPT.md`.

## Bot features
- `/start`: language (uz/ru/en) -> "what it does + how it works + limits" -> register (name, area)
- Several fields per farmer: location (pick a covered area or share GPS), crop, stage, groundwater, drainage, last flush, known salinity
- **Status**: irrigate / monitor / wait, salt-risk indicator, qualified flush hint, salt-aware crops, last-7-days signals
- **Plan**: 6-month outlook + 3-step rotation idea from ~2 years of past NASA POWER data (climatology, not a forecast)
- **Community**: posts per area / all areas, likes, report (3 reports hide a post), 5 posts/day limit
- **Alerts**: one morning message (07:00-20:00 Tashkent) per field when action may be needed; per-field and global switch
- Settings: language, area, alerts, delete account and all data
Code map: `app/bot.py` (handlers), `app/ui.py` (bot texts), `app/db.py` (SQLite), `app/regions.py` (covered areas), `app/engine/plan.py` (outlook)

## Architecture
```
Farmer -> Telegram bot (aiogram) --\
                                    >-> FastAPI (/api/advice, /api/map) -> advisor.build_advice()
Browser / Telegram Web App (Leaflet)/        |                                 |- irrigation.py (water balance + rules)
                                             |                                 |- salinity.py   (risk score)
              NASA POWER (history, soil wetness) + Open-Meteo (7-day forecast) |- flush.py      (qualified timing)
              cache 6 h per 0.5 deg cell; SQLite for bot users                 '- crops.py      (tolerance table)
```
- `app/data/` fetchers (NASA POWER, Open-Meteo, offline demo generator)
- `app/engine/` pure rule functions (unit-tested, no network)
- `app/messages.py` all text in en/uz/ru; engine returns keys, this renders them

## NASA data used
**NASA POWER** daily point API (community AG): `T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN, GWETROOT, GWETTOP`.
ET0 = Hargreaves-Samani (temperature + latitude). Root-zone wetness (`GWETROOT`) drives the irrigation rule.

## Status
Works offline (demo data), covered by tests: ET0, irrigation, salinity, flush, crops, API, 3 languages.
Verified live: NASA POWER (90 d and 2 y requests) and Open-Meteo respond. **NOT yet verified:** the bot against real Telegram
(only simulated updates) and the dashboard in a real browser. Community posts are not moderated beyond report/hide.

## Must be reviewed before we make any claim (owner: Yasmin)
- Kc values and `DRY/WATCH/MAX_DEFICIT` thresholds (`app/engine/crops.py`) vs FAO-56
- Salinity thresholds vs FAO Irrigation & Drainage Paper 29 / Maas & Hoffman (1977)
- Salt-risk weights (`salinity.py`) and flush rules (`flush.py`): current numbers are our assumptions
- Uzbek and Russian strings in `messages.py` (first drafts)
- That NASA POWER is listed in the resources of the challenge we select (Global Awards rule)

## Limitations (say these in the presentation)
POWER grid ~0.5 deg (~50 km): neighbouring fields look alike; no direct salinity measurement;
no field-level EC or groundwater data unless the farmer reports it; thresholds are generic, not calibrated locally.

## Sources to cite
NASA POWER (power.larc.nasa.gov); Open-Meteo (open-meteo.com); FAO Irrigation & Drainage Paper 56 (Allen et al. 1998);
Hargreaves & Samani (1985); Maas & Hoffman (1977) / FAO Paper 29; Leaflet; OpenStreetMap contributors; aiogram; FastAPI.

## AI tools used (disclose in submission)
Claude (Anthropic) assisted with planning, code generation and drafting of translations. All outputs are reviewed by the team.
