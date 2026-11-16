"""JSON API for the Telegram Mini App (served at /app). Every request carries Telegram's signed
`initData` in the X-Init-Data header; we verify the HMAC with the bot token, so a user can only
ever act as themselves."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

import asyncio
import datetime as dt

from . import config, db
from .appstrings import APP
from .engine import ai
from .engine.advisor import get_advice, get_plan, get_snapshot
from .engine.climate import climate_block
from .engine.cropfit import crop_cards
from .data import forecast as forecast_mod, nasa_power
from .engine.crops import CROPS, DRY_WETNESS, STAGES, WATCH_WETNESS, class_from_ece
from .engine.trace import irrigation_trace
from .rules import DATA as RULES_DATA, table as rules_table, val as rule_val
from .engine.plan import rotation_plan
from .engine.salinity import salinity_risk
from .messages import T as MSG, render, render_plan, t
from .regions import (AREA_GROUNDWATER, PILOTS, REGION_SALINITY, REGIONS, covered, nearest_region, region_name)
from .ui import (CROP_NAMES, DR_NAMES, EC_NAMES, FL_DAYS, FL_NAMES, GW_NAMES, STAGE_NAMES, UI, nm)

router = APIRouter(prefix="/api/app")
LANGS = ("uz", "ru", "en")


# ---------- auth ----------
def validate_init_data(init_data: str, token: str, max_age: int = 86400, now: float | None = None) -> int:
    """Returns the Telegram user id or raises ValueError. Algorithm: core.telegram.org/bots/webapps#validating-data"""
    if not init_data or not token:
        raise ValueError("missing")
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    got = parsed.pop("hash", None)
    if not got:
        raise ValueError("no hash")
    check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, got):
        raise ValueError("bad signature")
    if (now or time.time()) - int(parsed.get("auth_date", "0")) > max_age:
        raise ValueError("expired")
    return int(json.loads(parsed["user"])["id"])


def current_uid(x_init_data: str = Header(default="")) -> int:
    try:
        return validate_init_data(x_init_data, config.TELEGRAM_TOKEN)
    except Exception:
        raise HTTPException(401, "Open this app from Telegram.")


def registered_uid(uid: int = Depends(current_uid)) -> int:
    u = db.user_get(uid)
    if not u or not u["registered"]:
        raise HTTPException(403, "not registered")
    return uid


def own(uid: int, fid: int) -> dict:
    f = db.field_get(fid)
    if not f or f["user_id"] != uid:
        raise HTTPException(404, "field not found")
    return f


def lang_of(uid: int) -> str:
    return (db.user_get(uid) or {}).get("lang") or "uz"


def crop_names(lang: str) -> dict:
    return {k: nm(CROP_NAMES, k, lang) for k in CROPS}


# ---------- models ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    region: str
    lang: str = "uz"


class SettingsIn(BaseModel):
    lang: str | None = None
    region: str | None = None
    notify: bool | None = None
    alert_hour: int | None = Field(default=None, ge=5, le=10)


class FieldIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    region: str | None = None
    lat: float | None = None
    lon: float | None = None
    crop: str | None = None
    stage: str | None = None
    groundwater: str | None = None
    drainage: str | None = None
    last_flush: str | None = None      # key of FL_NAMES
    ec: str | None = None              # key of EC_NAMES
    notify: bool | None = None
    water: str | None = None           # normal | limited | scarce  (farmer priority)
    pref_crops: list[str] | None = None
    ece: float | None = Field(default=None, ge=0, le=60)         # MEASURED soil ECe, dS/m
    ece_date: str | None = None                                  # YYYY-MM-DD of the measurement
    water_ec: float | None = Field(default=None, ge=0, le=30)    # irrigation-water EC, dS/m
    clear_ece: bool = False
    clear_water_ec: bool = False


class EventIn(BaseModel):
    kind: str


class PostIn(BaseModel):
    text: str = Field(min_length=10, max_length=500)


def field_values(p: FieldIn) -> dict:
    v: dict = {}
    if p.name is not None:
        v["name"] = p.name.strip()
    for key, ok in (("crop", CROPS), ("stage", STAGES), ("groundwater", GW_NAMES), ("drainage", DR_NAMES)):
        choice = getattr(p, key)
        if choice is not None:
            if choice not in ok:
                raise HTTPException(422, f"bad {key}")
            v[key] = choice
    if p.last_flush is not None:
        if p.last_flush not in FL_DAYS:
            raise HTTPException(422, "bad last_flush")
        v["last_flush_days"] = FL_DAYS[p.last_flush]
    if p.ec is not None:
        if p.ec not in EC_NAMES:
            raise HTTPException(422, "bad ec")
        v["ec_class"] = None if p.ec == "unk" else p.ec
    if p.notify is not None:
        v["notify"] = 1 if p.notify else 0
    if p.clear_ece:
        v.update(ece=None, ece_date=None)
    elif p.ece is not None:
        day = today_or_422(p.ece_date)
        v.update(ece=p.ece, ece_date=day)
    if p.clear_water_ec:
        v["water_ec"] = None
    elif p.water_ec is not None:
        v["water_ec"] = p.water_ec
    if p.water is not None:
        if p.water not in ("normal", "limited", "scarce"):
            raise HTTPException(422, "bad water")
        v["water"] = p.water
    if p.pref_crops is not None:
        if any(c not in CROPS for c in p.pref_crops):
            raise HTTPException(422, "bad crop")
        v["pref_crops"] = ",".join(dict.fromkeys(p.pref_crops))
    if p.region is not None:
        if p.region not in REGIONS:
            raise HTTPException(422, "bad region")
        v.update(lat=REGIONS[p.region][0], lon=REGIONS[p.region][1], region=p.region)
    elif p.lat is not None and p.lon is not None:
        if not covered(p.lat, p.lon):
            raise HTTPException(422, "outside covered area")
        v.update(lat=p.lat, lon=p.lon, region=nearest_region(p.lat, p.lon))
    return v


def today_or_422(iso: str | None) -> str:
    """A measurement date: today by default; must be a real date that is not in the future."""
    if not iso:
        return dt.date.today().isoformat()
    try:
        d = dt.date.fromisoformat(iso)
    except ValueError:
        raise HTTPException(422, "bad date")
    if d > dt.date.today():
        raise HTTPException(422, "date in the future")
    return d.isoformat()


ECE_CLASS_BOUNDS = [2, 4, 8, 16]          # FAO soil salinity classes (dS/m): non / slightly / moderately / strongly / very strongly saline
WATER_CLASS_BOUNDS = [0.7, 3.0]           # FAO irrigation-water EC classes: no / slight-to-moderate / severe restriction


def measurement_block(p: dict) -> dict:
    out = {"ece": None, "ece_date": None, "ece_class": None, "age_days": None, "stale": False, "water_ec": p.get("water_ec"), "water_class": None}
    if p.get("ece") is not None:
        age = (dt.date.today() - dt.date.fromisoformat(p["ece_date"])).days if p.get("ece_date") else None
        out.update(ece=p["ece"], ece_date=p.get("ece_date"), ece_class=sum(p["ece"] >= b for b in ECE_CLASS_BOUNDS),
                   age_days=age, stale=age is not None and age > rule_val("ece_stale_days"))
    if p.get("water_ec") is not None:
        out["water_class"] = sum(p["water_ec"] >= b for b in WATER_CLASS_BOUNDS)
    return out


def prefs_of(f: dict) -> list[str]:
    return [c for c in (f.get("pref_crops") or "").split(",") if c in CROPS]


def field_out(f: dict) -> dict:
    fl_key = next((k for k, d in FL_DAYS.items() if d == f["last_flush_days"]), "unk")
    return {"id": f["id"], "name": f["name"], "lat": f["lat"], "lon": f["lon"], "region": f["region"],
            "crop": f["crop"], "stage": f["stage"], "groundwater": f["groundwater"], "drainage": f["drainage"],
            "last_flush": fl_key, "ec": f["ec_class"] or "unk", "notify": bool(f["notify"]),
            "water": f.get("water") or "normal", "prefs": prefs_of(f), "flush_days": db.flush_days(f),
            "ece": f.get("ece"), "ece_date": f.get("ece_date"), "water_ec": f.get("water_ec"),
            "ec_class": class_from_ece(f["ece"]) if f.get("ece") is not None else f["ec_class"]}


def post_out(p: dict, uid: int, lang: str) -> dict:
    return {"id": p["id"], "author": p["author"], "region": region_name(p["region"], lang), "created": p["created"],
            "text": p["text"], "likes": p.get("likes", 0), "mine": p["user_id"] == uid, "verified": p.get("role") == "agronomist"}


# ---------- bootstrap / account ----------
@router.get("/bootstrap")
def bootstrap(uid: int = Depends(current_uid)):
    db.user_upsert(uid)
    u = db.user_get(uid)
    reg = bool(u["registered"])
    return {
        "user": {"id": uid, "name": u["name"], "lang": u["lang"] or "uz", "region": u["region"], "notify": bool(u["notify"]),
                 "registered": reg, "alert_hour": u.get("alert_hour") or 7, "role": u.get("role") or "farmer"},
        "fields": [field_out(f) for f in db.fields_of(uid)] if reg else [],
        "meta": {
            "regions": [{"id": k, "lat": v[0], "lon": v[1], "name": v[2]} for k, v in REGIONS.items()],
            "crops": CROP_NAMES, "stages": STAGE_NAMES, "gw": GW_NAMES, "dr": DR_NAMES, "fl": FL_NAMES, "ec": EC_NAMES,
            "crop_order": list(CROPS), "stage_order": STAGES, "pilots": PILOTS,
            "thresholds": {"dry": DRY_WETNESS, "watch": WATCH_WETNESS},
            "ai": ai.enabled(),
        },
        "i18n": {**MSG, **UI, **APP},
    }


@router.post("/register")
def register(p: RegisterIn, uid: int = Depends(current_uid)):
    if p.region not in REGIONS or p.lang not in LANGS:
        raise HTTPException(422, "bad input")
    db.user_upsert(uid, name=p.name.strip(), region=p.region, lang=p.lang, registered=1)
    return {"ok": True}


@router.post("/settings")
def settings(p: SettingsIn, uid: int = Depends(current_uid)):
    kw = {}
    if p.lang is not None:
        if p.lang not in LANGS:
            raise HTTPException(422, "bad lang")
        kw["lang"] = p.lang
    if p.region is not None:
        if p.region not in REGIONS:
            raise HTTPException(422, "bad region")
        kw["region"] = p.region
    if p.notify is not None:
        kw["notify"] = 1 if p.notify else 0
    if p.alert_hour is not None:
        kw["alert_hour"] = p.alert_hour
    db.user_upsert(uid, **kw)
    return {"ok": True}


@router.delete("/account")
def delete_account(uid: int = Depends(registered_uid)):
    db.user_delete(uid)
    return {"ok": True}


# ---------- fields ----------
@router.post("/fields")
def create_field(p: FieldIn, uid: int = Depends(registered_uid)):
    if len(db.fields_of(uid)) >= 10:
        raise HTTPException(422, "max 10 fields")
    v = field_values(p)
    if not p.name or "lat" not in v:
        raise HTTPException(422, "name and location required")
    fid = db.field_add(uid, v.pop("name"), v.get("region"))
    db.field_update(fid, **v)
    return field_out(db.field_get(fid))


@router.put("/fields/{fid}")
def update_field(fid: int, p: FieldIn, uid: int = Depends(registered_uid)):
    own(uid, fid)
    db.field_update(fid, **field_values(p))
    return field_out(db.field_get(fid))


@router.delete("/fields/{fid}")
def delete_field(fid: int, uid: int = Depends(registered_uid)):
    own(uid, fid)
    db.field_delete(fid)
    return {"ok": True}


def field_params(f: dict) -> dict:
    """What the engine needs. A MEASURED ECe takes precedence over the farmer's low/medium/high guess."""
    ece = f.get("ece")
    return {**f, "last_flush_days": db.flush_days(f), "prefs": prefs_of(f), "water": f.get("water") or "normal",
            "ec_class": class_from_ece(ece) if ece is not None else f["ec_class"], "ece": ece, "water_ec": f.get("water_ec"),
            "since_irrigation": db.last_event_days(f["id"], "irrigated")}


def area_params(rid: str, crop: str = "cotton", stage: str = "mid") -> dict:
    """District-level view: a typical field at the district centre (placeholder defaults, clearly labelled in the UI)."""
    if rid not in REGIONS:
        raise HTTPException(404, "area not found")
    if crop not in CROPS or stage not in STAGES:
        raise HTTPException(422, "bad crop or stage")
    return {"id": None, "name": rid, "lat": REGIONS[rid][0], "lon": REGIONS[rid][1], "region": rid, "crop": crop, "stage": stage,
            "groundwater": AREA_GROUNDWATER.get(rid, "unknown"), "drainage": "unknown", "last_flush_days": None,
            "ec_class": None, "water": "normal", "prefs": [], "ece": None, "ece_date": None, "water_ec": None, "since_irrigation": None}


def target_out(p: dict, lang: str) -> dict:
    is_field = bool(p.get("id"))
    return {"type": "field" if is_field else "area", "id": p["id"] if is_field else p["region"],
            "name": p["name"] if is_field else region_name(p["region"], lang),
            "lat": p["lat"], "lon": p["lon"], "region": p["region"], "crop": p["crop"], "stage": p["stage"]}


async def status_payload(p: dict, lang: str, refresh: bool = False) -> dict:
    try:
        series, forecast = await get_snapshot(p["lat"], p["lon"], refresh=refresh)
        if not series:
            raise RuntimeError("NASA POWER returned no data")
        a = await get_advice(p["lat"], p["lon"], crop=p["crop"], stage=p["stage"], groundwater=p["groundwater"],
                             drainage=p["drainage"], last_flush_days=p["last_flush_days"], ec_class=p["ec_class"],
                             ece=p["ece"], water_ec=p["water_ec"], since_irrigation=p.get("since_irrigation"))
    except Exception as e:
        raise HTTPException(502, f"NASA data unavailable: {e}")
    stat = REGION_SALINITY.get(p["region"])
    return {"target": target_out(p, lang), "advice": a, "text": render(a, lang, crop_names(lang)),
            "climate": climate_block(series, forecast, p["lat"]), "salt_measured": p["ece"] is not None,
            "measurement": measurement_block(p), "trace": irrigation_trace(a["irrigation"]["metrics"], a["irrigation"]["status"], lang),
            "rules": {"version": RULES_DATA["version"], "validated_by": RULES_DATA["validated_by"]},
            "data_stale": nasa_power.META["stale_used"],
            "flush_days": p["last_flush_days"], "regional": {"region": stat[0], "pct": stat[1]} if stat else None}


async def crops_payload(p: dict, lang: str) -> dict:
    try:
        series, _ = await get_snapshot(p["lat"], p["lon"])
    except Exception as e:
        raise HTTPException(502, f"NASA data unavailable: {e}")
    sal = salinity_risk(series, p["lat"], p["groundwater"], p["last_flush_days"], p["ec_class"])
    cards = crop_cards(sal["level"], p["ec_class"], p["water"], p["prefs"], p["crop"], p["ece"])
    names = crop_names(lang)
    rot = rotation_plan(p["crop"], cards["level"], p["ec_class"], p["water"], tuple(p["prefs"]), p["ece"])
    for c in cards["crops"]:
        c["name"] = names[c["crop"]]
    return {"target": target_out(p, lang), "level": cards["level"], "level_text": t("lv_" + cards["level"], lang),
            "assumed_ec": cards["assumed_ec"], "ec_known": p["ece"] is not None, "measurement": measurement_block(p), "ec_class_guess": bool(p["ec_class"]) and p["ece"] is None, "score": sal["score"], "crops": cards["crops"],
            "water": p["water"], "prefs": p["prefs"], "rotation_key": cards["rotation_key"],
            "rotation": [names.get(x["crop"], x["crop"]) if x["kind"] == "crop" else t("plan_leach_step", lang) for x in rot],
            "rotation_text": t(cards["rotation_key"], lang)}


async def plan_payload(p: dict, lang: str) -> dict:
    try:
        plan = await get_plan(p["lat"], p["lon"], crop=p["crop"], groundwater=p["groundwater"], drainage=p["drainage"],
                              last_flush_days=p["last_flush_days"], ec_class=p["ec_class"], water=p["water"], prefs=tuple(p["prefs"]), ece=p["ece"])
    except Exception as e:
        raise HTTPException(502, f"NASA data unavailable: {e}")
    months = t("months", lang).split()
    names = crop_names(lang)
    return {
        "level": plan["level"], "level_text": t("lv_" + plan["level"], lang),
        "outlook": [{"month": months[o["month"] - 1], "key": o["key"], "text": t(o["key"], lang, **o["params"])} for o in plan["outlook"]],
        "trend": t(plan["trend"]["key"], lang, **plan["trend"]["params"]) if plan.get("trend") else None,
        "rotation": [names.get(s["crop"], s["crop"]) if s["kind"] == "crop" else t("plan_leach_step", lang) for s in plan["rotation"]],
        "disclaimer": t("plan_disc", lang, days=plan["history_days"]),
        "text": render_plan(plan, lang, names),
    }


@router.get("/fields/{fid}/status")
async def field_status(fid: int, refresh: bool = False, uid: int = Depends(registered_uid)):
    f, lang = own(uid, fid), lang_of(uid)
    out = await status_payload(field_params(f), lang, refresh)
    db.log_advice(fid, out["advice"])
    out["history"] = [h["irrigation"] for h in db.recent_log(fid, 7)]
    out["events"] = db.events_of(fid)
    out["field"] = field_out(db.field_get(fid))
    return out


class AskIn(BaseModel):
    question: str = Field(default="", max_length=ai.MAX_Q)


@router.post("/fields/{fid}/ask")
async def field_ask(fid: int, p: AskIn, uid: int = Depends(registered_uid)):
    """AI explanation of the rule engine's current advice (Gemini). Falls back to the rule text if AI is unavailable."""
    f, lang = own(uid, fid), lang_of(uid)
    out = await status_payload(field_params(f), lang)
    try:
        return {"answer": await ai.ask(uid, fid, lang, out, p.question), "ai": True}
    except ai.AILimit:
        raise HTTPException(429, "limit")
    except ai.AIError:
        return {"answer": out["text"]["irrigation_reason"], "ai": False}


@router.post("/area/{rid}/ask")
async def area_ask(rid: str, p: AskIn, uid: int = Depends(registered_uid)):
    """Same as /fields/{fid}/ask, for the district view (a farmer without a field yet)."""
    lang = lang_of(uid)
    out = await status_payload(area_params(rid), lang)
    try:
        return {"answer": await ai.ask(uid, rid, lang, out, p.question), "ai": True}
    except ai.AILimit:
        raise HTTPException(429, "limit")
    except ai.AIError:
        return {"answer": out["text"]["irrigation_reason"], "ai": False}


@router.get("/fields/{fid}/crops")
async def field_crops(fid: int, uid: int = Depends(registered_uid)):
    return await crops_payload(field_params(own(uid, fid)), lang_of(uid))


@router.get("/fields/{fid}/plan")
async def field_plan(fid: int, uid: int = Depends(registered_uid)):
    return await plan_payload(field_params(own(uid, fid)), lang_of(uid))


@router.post("/fields/{fid}/events")
def add_event(fid: int, p: EventIn, uid: int = Depends(registered_uid)):
    own(uid, fid)
    if p.kind not in ("irrigated", "flushed", "sown", "harvested"):
        raise HTTPException(422, "bad kind")
    db.event_add(fid, p.kind)
    if p.kind == "flushed":
        db.field_update(fid, flush_date=dt.date.today().isoformat())
    elif p.kind == "sown":
        db.field_update(fid, stage="initial")
    elif p.kind == "harvested":
        db.field_update(fid, stage="fallow")
    return {"field": field_out(db.field_get(fid)), "events": db.events_of(fid)}


@router.get("/area/{rid}/status")
async def area_status(rid: str, crop: str = "cotton", stage: str = "mid", refresh: bool = False, uid: int = Depends(current_uid)):
    return await status_payload(area_params(rid, crop, stage), lang_of(uid), refresh)


@router.get("/area/{rid}/crops")
async def area_crops(rid: str, uid: int = Depends(current_uid)):
    return await crops_payload(area_params(rid), lang_of(uid))


@router.get("/area/{rid}/plan")
async def area_plan(rid: str, uid: int = Depends(current_uid)):
    return await plan_payload(area_params(rid), lang_of(uid))


@router.get("/rules")
def rules(uid: int = Depends(current_uid)):
    """The editable thresholds table (app/rules.json), labelled in the user's language."""
    return rules_table(lang_of(uid))


@router.get("/sources")
def sources(uid: int = Depends(current_uid)):
    """Dataset log for the About screen: what is used, at what resolution, which API version, when last accessed."""
    P = nasa_power.META
    return [
        {"name": "NASA POWER", "product": P["api_name"], "version": P["api_version"], "resolution": "~0.5° × 0.625° (50–70 km), daily",
         "params": ", ".join(nasa_power.PARAMS), "accessed": P["accessed"], "stale": P["stale_used"], "kind": "nasa"},
        {"name": "Open-Meteo", "product": "Forecast API (7 days)", "version": None, "resolution": "~11 km, daily",
         "params": "precipitation_sum, temperature_2m_max/min", "accessed": forecast_mod.META["accessed"], "stale": False, "kind": "other"},
        {"name": "NASA GIBS", "product": "MODIS Terra true colour (daily) and NDVI (8-day), map layers", "version": None, "resolution": "250 m - 1 km (visual only)",
         "params": "image tiles", "accessed": None, "stale": False, "kind": "nasa"},
        {"name": "FAO", "product": "Irrigation & Drainage Papers 29 and 56", "version": "1985 / 1998", "resolution": "reference tables",
         "params": "crop salt tolerance, water-quality classes, crop water use", "accessed": None, "stale": False, "kind": "other"},
    ]


@router.get("/map")
async def map_points(uid: int = Depends(registered_uid)):
    """Pilot districts + the farmer's own fields, each with today's irrigation signal (cached NASA data)."""
    lang = lang_of(uid)
    items = [{"kind": "area", "pilot": True, **area_params(rid), "name": region_name(rid, lang), "id": rid} for rid in PILOTS]
    items += [{"kind": "field", "pilot": False, **field_params(f)} for f in db.fields_of(uid)]

    async def one(it):
        a = await get_advice(it["lat"], it["lon"], crop=it["crop"], stage=it["stage"], groundwater=it["groundwater"],
                             drainage=it["drainage"], last_flush_days=it["last_flush_days"], ec_class=it["ec_class"],
                             ece=it.get("ece"), water_ec=it.get("water_ec"), since_irrigation=it.get("since_irrigation"))
        return {"kind": it["kind"], "id": it["id"], "name": it["name"], "lat": it["lat"], "lon": it["lon"], "pilot": it["pilot"],
                "region": it["region"], "status": a["irrigation"]["status"], "level": a["salinity"]["level"], "score": a["salinity"]["score"],
                "status_text": t("st_" + a["irrigation"]["status"], lang), "level_text": t("lv_" + a["salinity"]["level"], lang)}
    res = await asyncio.gather(*(one(i) for i in items), return_exceptions=True)
    return [r for r in res if not isinstance(r, Exception)]


# ---------- community ----------
@router.get("/posts")
def list_posts(scope: str = "region", uid: int = Depends(registered_uid)):
    lang = lang_of(uid)
    if scope == "mine":
        posts = db.posts_of(uid, 20)
    elif scope == "all":
        posts = db.posts_latest(None, 20)
    else:
        posts = db.posts_latest((db.user_get(uid) or {}).get("region"), 20)
    return [post_out(p, uid, lang) for p in posts]


@router.post("/posts")
def create_post(p: PostIn, uid: int = Depends(registered_uid)):
    text = p.text.strip()
    if len(text) < 10:
        raise HTTPException(422, "too short")
    if db.posts_today(uid) >= 5:
        raise HTTPException(429, "daily limit")
    u = db.user_get(uid)
    db.post_add(uid, u["name"] or nm(UI, "farmer", lang_of(uid)), u["region"], text)
    return {"ok": True}


def visible_post(pid: int) -> dict:
    p = db.post_get(pid)
    if not p or p["hidden"]:
        raise HTTPException(404, "post not found")
    return p


@router.post("/posts/{pid}/like")
def like(pid: int, uid: int = Depends(registered_uid)):
    visible_post(pid)
    return {"likes": db.like_toggle(pid, uid)}


@router.post("/posts/{pid}/report")
def report(pid: int, uid: int = Depends(registered_uid)):
    visible_post(pid)
    return {"new": db.report_post(pid, uid)}


@router.delete("/posts/{pid}")
def delete_post(pid: int, uid: int = Depends(registered_uid)):
    p = visible_post(pid)
    if p["user_id"] != uid:
        raise HTTPException(403, "not yours")
    db.post_delete(pid)
    return {"ok": True}
