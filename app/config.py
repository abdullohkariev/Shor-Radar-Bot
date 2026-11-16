import os
import pathlib


def _load_env_file():
    """Tiny .env reader (KEY=VALUE per line) so no extra package is needed. Real env vars win."""
    f = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


_load_env_file()

DEMO_MODE = os.getenv("SHOR_DEMO", "0") == "1"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")                 # optional: enables the "Ask AI" box
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Public HTTPS address of the Mini App (the cloudflared tunnel URL while the laptop is on). Set it in .env.
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
AI_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "15"))        # "Ask AI" questions per farmer per day (counted in the local database)
AI_GLOBAL_LIMIT = int(os.getenv("AI_GLOBAL_LIMIT", "300"))      # across all farmers per day: keeps the free quota from running out

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DB_PATH = os.getenv("SHOR_DB", "shor_radar.db")
CACHE_DIR = os.getenv("SHOR_CACHE", str(pathlib.Path(__file__).resolve().parent.parent / "cache"))   # disk copy of NASA data
POWER_CACHE_TTL = 6 * 3600  # seconds
