import asyncio
import collections
import pathlib
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .engine.advisor import get_advice
from .engine.crops import CROPS, STAGES
from . import db
from .messages import render
from .webapp_api import router as webapp_router

app = FastAPI(title="Sho'r Radar API", version="0.3")
db.init()
app.include_router(webapp_router)

# The old open demo endpoints (/api/advice, /api/map) need no login and call NASA, so on a public server they get a per-IP limit.
_HITS: dict = collections.defaultdict(collections.deque)
OPEN_LIMIT, OPEN_WINDOW = 30, 60          # requests per IP per minute


@app.middleware("http")
async def limit_open_endpoints(request: Request, call_next):
    if request.url.path in ("/api/advice", "/api/map"):
        ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?"))
        now, q = time.time(), _HITS[ip]
        while q and now - q[0] > OPEN_WINDOW:
            q.popleft()
        if len(q) >= OPEN_LIMIT:
            return JSONResponse({"detail": "Too many requests, try again in a minute."}, status_code=429)
        q.append(now)
    return await call_next(request)


@app.get("/app")
def mini_app():
    """Telegram Mini App entry point (no-store so edits show up immediately)."""
    return FileResponse(pathlib.Path(__file__).parent / "static" / "app.html", headers={"Cache-Control": "no-store"})

DEMO_FIELDS = [
    {"id": "urgench", "name": "Urgench, Khorezm", "lat": 41.55, "lon": 60.63, "crop": "cotton", "groundwater": "shallow"},
    {"id": "khiva", "name": "Khiva, Khorezm", "lat": 41.38, "lon": 60.36, "crop": "wheat", "groundwater": "shallow"},
    {"id": "nukus", "name": "Nukus, Karakalpakstan", "lat": 42.46, "lon": 59.61, "crop": "cotton", "groundwater": "shallow"},
    {"id": "muynak", "name": "Muynak, Karakalpakstan", "lat": 43.77, "lon": 59.02, "crop": "barley", "groundwater": "shallow"},
    {"id": "bukhara", "name": "Bukhara", "lat": 39.77, "lon": 64.42, "crop": "cotton", "groundwater": "medium"},
    {"id": "navoi", "name": "Navoi", "lat": 40.10, "lon": 65.37, "crop": "wheat", "groundwater": "medium"},
    {"id": "gulistan", "name": "Gulistan, Syrdarya", "lat": 40.49, "lon": 68.78, "crop": "wheat", "groundwater": "medium"},
    {"id": "fergana", "name": "Fergana", "lat": 40.38, "lon": 71.78, "crop": "maize", "groundwater": "deep"},
]


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/meta")
def meta():
    return {"crops": list(CROPS), "stages": STAGES}


@app.get("/api/advice")
async def api_advice(
    lat: float = Query(..., ge=37, le=46), lon: float = Query(..., ge=55, le=74),
    crop: str = "cotton", stage: str = "mid", groundwater: str = "unknown", drainage: str = "unknown",
    last_flush_days: int | None = Query(None, ge=0), ec_class: str | None = None,
    lang: str = "en", demo: bool | None = None,
):
    if crop not in CROPS:
        raise HTTPException(422, f"crop must be one of {list(CROPS)}")
    if stage not in STAGES:
        raise HTTPException(422, f"stage must be one of {STAGES}")
    try:
        advice = await get_advice(lat, lon, demo=demo, crop=crop, stage=stage, groundwater=groundwater,
                                  drainage=drainage, last_flush_days=last_flush_days, ec_class=ec_class)
    except Exception as e:  # network / NASA outage
        raise HTTPException(502, f"Data source unavailable: {e}")
    advice["text"] = render(advice, lang)
    return advice


@app.get("/api/map")
async def api_map(lang: str = "en", demo: bool | None = None):
    async def one(f):
        a = await get_advice(f["lat"], f["lon"], demo=demo, crop=f["crop"], stage="mid",
                             groundwater=f["groundwater"])
        a["text"] = render(a, lang)
        return {**f, "advice": a}
    res = await asyncio.gather(*(one(f) for f in DEMO_FIELDS), return_exceptions=True)
    return [r for r in res if not isinstance(r, Exception)]


app.mount("/", StaticFiles(directory=pathlib.Path(__file__).parent / "static", html=True), name="static")
