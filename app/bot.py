"""Telegram bot (aiogram 3). Run:  python -m app.bot

Flow: /start -> language -> about -> register (name, area) -> add field -> status / plan / community.
Callback data always carries the field id; every handler re-checks that the field belongs to the user."""
import asyncio
import datetime as dt
import logging
import time
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (MenuButtonWebApp, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo)

from . import config, db
from .engine.advisor import get_advice, get_plan, get_snapshot
from .engine.crops import class_from_ece
from .rules import val as rule_val
from .engine.crops import CROPS, STAGES
from .appstrings import APP
from .messages import EMOJI, render, render_plan, t as msg_t
from .regions import PILOTS, REGIONS, covered, nearest_region, region_name
from .engine import ai
from .ui import (CROP_NAMES, DR_NAMES, EC_NAMES, FL_DAYS, FL_NAMES, GW_NAMES, LANG_BUTTONS, STAGE_NAMES, nm, tr, UI)

dp = Dispatcher(storage=MemoryStorage())
try:
    TZ = ZoneInfo("Asia/Tashkent")
except Exception:                       # Windows without the tzdata package; Uzbekistan has no DST
    TZ = dt.timezone(dt.timedelta(hours=5))
MAX_FIELDS = 10
MENU_KEYS = ["m_status", "m_fields", "m_add", "m_plan", "m_comm", "m_set", "m_about"]


class Reg(StatesGroup):
    name = State()


class Fld(StatesGroup):
    name = State()
    loc = State()


class Post(StatesGroup):
    text = State()


# ---------------- helpers ----------------
def lang_of(uid: int) -> str:
    u = db.user_get(uid)
    return (u or {}).get("lang") or "uz"


def labels(key: str) -> set[str]:
    return set(UI[key].values())


def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def ikb(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chunk(buttons, n):
    return [buttons[i:i + n] for i in range(0, len(buttons), n)]


def app_url() -> str | None:
    """Mini App address (needs HTTPS, so only set when WEBAPP_URL is configured)."""
    return config.WEBAPP_URL.rstrip("/") + "/app" if config.WEBAPP_URL.startswith("https://") else None


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=tr(k, lang)) for k in r]
            for r in (["m_status", "m_fields"], ["m_add", "m_plan"], ["m_comm", "m_set"], ["m_about"])]
    if app_url():
        rows.insert(0, [KeyboardButton(text=tr("m_app", lang))])   # plain button: apps opened from a keyboard get no login data, so we answer with an inline button
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


async def app_only(m: Message):
    """When the Mini App is configured, the bot's only job is to open it: drop the old bottom keyboard
    and show one big Open app button."""
    u = db.user_get(m.from_user.id)
    lang = (u or {}).get("lang") if u and u["registered"] else None
    text = tr("app_welcome", lang) if lang else "\n\n".join(UI["app_welcome"][l] for l in ("uz", "ru", "en"))
    await m.answer(text, reply_markup=ReplyKeyboardRemove())
    await m.answer("👇", reply_markup=open_app_kb(lang or "uz"))


def open_app_kb(lang: str):
    return ikb([[InlineKeyboardButton(text=tr("m_app", lang), web_app=WebAppInfo(url=app_url()))]]) if app_url() else None


def loc_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=tr("loc_btn", lang), request_location=True)]],
                               resize_keyboard=True, one_time_keyboard=True)


def region_buttons(prefix: str, lang: str):
    return chunk([btn(region_name(rid, lang), f"{prefix}:{rid}") for rid in REGIONS], 2)


def crop_names_for(lang: str) -> dict:
    return {k: nm(CROP_NAMES, k, lang) for k in CROPS}


def registered(uid: int) -> bool:
    u = db.user_get(uid)
    return bool(u and u["registered"])


def own_field(uid: int, fid_str: str):
    """Return the field only if it belongs to this user (prevents tampering with callback data)."""
    try:
        f = db.field_get(int(fid_str))
    except ValueError:
        return None
    return f if f and f["user_id"] == uid else None


async def typing(m: Message):
    try:
        await m.bot.send_chat_action(m.chat.id, "typing")
    except Exception:
        pass


# ---------------- start / language / about / registration ----------------
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    if app_url():
        return await app_only(m)
    db.user_upsert(m.from_user.id)
    if registered(m.from_user.id):
        lang = lang_of(m.from_user.id)
        return await m.answer(tr("menu_hint", lang), reply_markup=main_menu(lang))
    text = "\n\n".join(UI["welcome"][l] for l in ("uz", "ru", "en"))
    await m.answer(text, reply_markup=ikb([[btn(t, f"lang:{c}") for t, c in LANG_BUTTONS]]))


@dp.message(F.func(lambda m: bool(app_url())), ~Command("app"))
async def app_mode_catch_all(m: Message, state: FSMContext):
    """App-only mode. A typed question gets an AI answer about the farmer's field (when AI is on and they are registered);
    everything else, including taps on the old bottom keyboard, just gets the Open app button."""
    await state.clear()
    if (m.text and not m.text.startswith("/") and ai.enabled() and registered(m.from_user.id)
            and m.text not in _OLD_KEYBOARD_TEXTS):
        return await ai_reply(m)
    await app_only(m)


_OLD_KEYBOARD_TEXTS = set().union(*(set(UI[k].values()) for k in ("m_status", "m_fields", "m_add", "m_plan", "m_comm", "m_set", "m_about", "m_app")))


def _app_text(key: str, lang: str) -> str:
    e = APP[key]
    return e.get(lang, e["en"])


async def ai_reply(m: Message):
    """Answer a typed question about the farmer's own field with the same Gemini helper the Mini App uses."""
    from . import webapp_api as wa
    uid = m.from_user.id
    lang = lang_of(uid)
    q = (m.text or "").strip()[:ai.MAX_Q]
    fields = db.fields_of(uid)
    f = next((x for x in fields if x["name"] and x["name"].lower() in q.lower()), None) or (fields[0] if fields else None)
    params = wa.field_params(f) if f else wa.area_params((db.user_get(uid) or {}).get("region") or PILOTS[0])
    await typing(m)
    try:
        out = await wa.status_payload(params, lang)
    except Exception:
        logging.exception("ai_reply: status failed")
        return await m.answer(tr("err", lang), reply_markup=open_app_kb(lang))
    note = ""
    try:
        answer = await ai.ask(uid, f["id"] if f else params["region"], lang, out, q)
        note = "\n\n🤖 " + _app_text("ai_note", lang)
    except ai.AILimit:
        answer = _app_text("ai_limit", lang)
    except ai.AIError:
        answer = out["text"]["irrigation_reason"]
    head = f"📍 {f['name']}\n\n" if f else ""
    await m.answer(head + answer + note, reply_markup=open_app_kb(lang))


@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]
    if lang not in ("uz", "ru", "en"):
        return await c.answer()
    db.user_upsert(c.from_user.id, lang=lang)
    if registered(c.from_user.id):
        await c.message.answer(tr("updated", lang), reply_markup=main_menu(lang))
    else:
        await c.message.answer(tr("about", lang), reply_markup=ikb([[btn(tr("btn_register", lang), "reg")]]))
    await c.answer()


@dp.callback_query(F.data == "reg")
async def reg_start(c: CallbackQuery, state: FSMContext):
    lang = lang_of(c.from_user.id)
    await state.set_state(Reg.name)
    await c.message.answer(tr("ask_name", lang), reply_markup=ReplyKeyboardRemove())
    await c.answer()


@dp.message(Reg.name, F.text)
async def reg_name(m: Message, state: FSMContext):
    lang = lang_of(m.from_user.id)
    name = m.text.strip()
    if not 2 <= len(name) <= 40 or name.startswith("/"):
        return await m.answer(tr("name_bad", lang))
    db.user_upsert(m.from_user.id, name=name)
    await state.clear()
    await m.answer(tr("ask_region", lang), reply_markup=loc_keyboard(lang))
    await m.answer("👇", reply_markup=ikb(region_buttons("rgn", lang)))


async def complete_region(m: Message, uid: int, rid: str, state: FSMContext):
    """Used for both registration and 'change my area' in settings."""
    lang = lang_of(uid)
    first_time = not registered(uid)
    db.user_upsert(uid, region=rid, registered=1)
    if first_time:
        u = db.user_get(uid)
        await m.answer(tr("reg_done", lang, name=u["name"] or ""), reply_markup=main_menu(lang))
        await begin_add_field(m, uid, state)
    else:
        await m.answer(f"{tr('updated', lang)} {region_name(rid, lang)}", reply_markup=main_menu(lang))


@dp.callback_query(F.data.startswith("rgn:"))
async def pick_region(c: CallbackQuery, state: FSMContext):
    rid = c.data.split(":")[1]
    u = db.user_get(c.from_user.id)
    if rid not in REGIONS or not u or not u["name"]:
        return await c.answer()
    await state.clear()
    await complete_region(c.message, c.from_user.id, rid, state)
    await c.answer()


# ---------------- add field ----------------
async def begin_add_field(m: Message, uid: int, state: FSMContext):
    lang = lang_of(uid)
    if len(db.fields_of(uid)) >= MAX_FIELDS:
        return await m.answer(tr("max_fields", lang, n=MAX_FIELDS), reply_markup=main_menu(lang))
    await state.set_state(Fld.name)
    await m.answer(tr("ask_fname", lang), reply_markup=ReplyKeyboardRemove())


@dp.message(F.text.in_(labels("m_add")))
@dp.message(Command("field"))
async def menu_add(m: Message, state: FSMContext):
    await state.clear()
    if not registered(m.from_user.id):
        return await m.answer(tr("need_reg", lang_of(m.from_user.id)))
    await begin_add_field(m, m.from_user.id, state)


@dp.message(Fld.name, F.text)
async def fld_name(m: Message, state: FSMContext):
    lang = lang_of(m.from_user.id)
    name = m.text.strip()
    if not 1 <= len(name) <= 40 or name.startswith("/"):
        return await m.answer(tr("name_bad", lang))
    u = db.user_get(m.from_user.id)
    fid = db.field_add(m.from_user.id, name, u["region"])
    await state.update_data(fid=fid)
    await state.set_state(Fld.loc)
    await m.answer(tr("ask_floc", lang), reply_markup=loc_keyboard(lang))
    await m.answer("👇", reply_markup=ikb(region_buttons(f"floc:{fid}", lang)))


async def apply_location(m: Message, uid: int, fid: int, lat: float, lon: float, rid: str):
    lang = lang_of(uid)
    db.field_update(fid, lat=lat, lon=lon, region=rid)
    await m.answer(f"📍 {region_name(rid, lang)}", reply_markup=main_menu(lang))
    crops = list(CROPS)
    rows = chunk([btn(nm(CROP_NAMES, k, lang), f"crop:{fid}:{k}") for k in crops], 3)
    await m.answer(tr("crop_q", lang), reply_markup=ikb(rows))


@dp.callback_query(F.data.startswith("floc:"))
async def field_loc_cb(c: CallbackQuery, state: FSMContext):
    _, fid, rid = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or rid not in REGIONS:
        return await c.answer(tr("field_gone", lang_of(c.from_user.id)), show_alert=True)
    await state.clear()
    lat, lon, _ = REGIONS[rid]
    await apply_location(c.message, c.from_user.id, f["id"], lat, lon, rid)
    await c.answer()


@dp.message(F.location)
async def got_location(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    lat, lon = m.location.latitude, m.location.longitude
    if not covered(lat, lon):
        return await m.answer(tr("loc_out", lang))
    rid = nearest_region(lat, lon)
    cur = await state.get_state()
    if cur == Fld.loc.state:
        f = own_field(uid, str((await state.get_data()).get("fid", "")))
        if not f:
            await state.clear()
            return await m.answer(tr("field_gone", lang))
        await state.clear()
        return await apply_location(m, uid, f["id"], lat, lon, rid)
    if not registered(uid) and (db.user_get(uid) or {}).get("name"):
        await state.clear()
        return await complete_region(m, uid, rid, state)
    # location sent outside any flow: ignore politely
    await m.answer(tr("menu_hint", lang), reply_markup=main_menu(lang) if registered(uid) else None)


@dp.callback_query(F.data.startswith("crop:"))
async def got_crop(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, crop = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or crop not in CROPS:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], crop=crop)
    await c.message.answer(tr("stage_q", lang), reply_markup=ikb(
        [[btn(nm(STAGE_NAMES, s, lang), f"stage:{f['id']}:{s}")] for s in STAGES]))
    await c.answer()


@dp.callback_query(F.data.startswith("stage:"))
async def got_stage(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, stage = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or stage not in STAGES:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], stage=stage)
    await ask_gw(c.message, f["id"], lang)
    await c.answer()


async def ask_gw(m: Message, fid: int, lang: str):
    await m.answer(tr("gw_q", lang), reply_markup=ikb(chunk([btn(nm(GW_NAMES, k, lang), f"gw:{fid}:{k}") for k in GW_NAMES], 2)))


@dp.callback_query(F.data.startswith("gw:"))
async def got_gw(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, v = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or v not in GW_NAMES:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], groundwater=v)
    await c.message.answer(tr("dr_q", lang), reply_markup=ikb([[btn(nm(DR_NAMES, k, lang), f"dr:{f['id']}:{k}")] for k in DR_NAMES]))
    await c.answer()


@dp.callback_query(F.data.startswith("dr:"))
async def got_dr(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, v = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or v not in DR_NAMES:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], drainage=v)
    await c.message.answer(tr("fl_q", lang), reply_markup=ikb([[btn(nm(FL_NAMES, k, lang), f"fl:{f['id']}:{k}")] for k in FL_NAMES]))
    await c.answer()


@dp.callback_query(F.data.startswith("fl:"))
async def got_fl(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, v = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or v not in FL_DAYS:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], last_flush_days=FL_DAYS[v])
    await c.message.answer(tr("ec_q", lang), reply_markup=ikb(chunk([btn(nm(EC_NAMES, k, lang), f"ec:{f['id']}:{k}") for k in EC_NAMES], 2)))
    await c.answer()


@dp.callback_query(F.data.startswith("ec:"))
async def got_ec(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, v = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or v not in EC_NAMES:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], ec_class=None if v == "unk" else v)
    await c.message.answer(tr("saved", lang), reply_markup=main_menu(lang))
    await send_status(c.message, c.from_user.id, f["id"])
    await c.answer()


# ---------------- status / plan ----------------
async def field_advice_text(f: dict, lang: str) -> str:
    a = await get_advice(f["lat"], f["lon"], crop=f["crop"], stage=f["stage"], groundwater=f["groundwater"],
                         drainage=f["drainage"], last_flush_days=db.flush_days(f), ec_class=f["ec_class"])
    db.log_advice(f["id"], a)
    head = f"📍 {f['name']} — {nm(CROP_NAMES, f['crop'], lang)}, {nm(STAGE_NAMES, f['stage'], lang)}\n\n"
    body = render(a, lang, crop_names_for(lang))["message"]
    extra = ""
    if not f["ec_class"]:
        extra += "\n\n🧪 " + tr("salt_unknown", lang)
    hist = db.recent_log(f["id"], 7)
    if len(hist) > 1:
        sym = {"IRRIGATE": "💧", "MONITOR": "👀", "WAIT": "⏳"}
        extra += f"\n\n📈 {tr('recent', lang)}: " + " ".join(sym.get(h["irrigation"], "?") for h in hist)
    return head + body + extra


async def send_status(m: Message, uid: int, fid: int):
    lang = lang_of(uid)
    f = own_field(uid, str(fid))
    if not f:
        return await m.answer(tr("field_gone", lang))
    await typing(m)
    try:
        text = await field_advice_text(f, lang)
    except Exception:
        logging.exception("advice failed")
        return await m.answer(tr("err", lang))
    await m.answer(text, reply_markup=ikb([[btn(tr("b_plan", lang), f"fpl:{f['id']}"), btn(tr("b_stage", lang), f"fstg:{f['id']}")]]))


async def send_plan(m: Message, uid: int, fid: int):
    lang = lang_of(uid)
    f = own_field(uid, str(fid))
    if not f:
        return await m.answer(tr("field_gone", lang))
    await typing(m)
    try:
        plan = await get_plan(f["lat"], f["lon"], crop=f["crop"], groundwater=f["groundwater"], drainage=f["drainage"],
                              last_flush_days=db.flush_days(f), ec_class=f["ec_class"])
    except Exception:
        logging.exception("plan failed")
        return await m.answer(tr("err", lang))
    names = {k: nm(CROP_NAMES, k, lang) for k in CROPS}
    await m.answer(f"📍 {f['name']}\n\n" + render_plan(plan, lang, names))


async def choose_field(m: Message, uid: int, action: str):
    """action: 'fst' (status) or 'fpl' (plan). One field -> run immediately, else ask which."""
    lang = lang_of(uid)
    fields = db.fields_of(uid)
    if not fields:
        return await m.answer(tr("nofield", lang))
    if len(fields) == 1:
        return await (send_status if action == "fst" else send_plan)(m, uid, fields[0]["id"])
    await m.answer(tr("which_field", lang), reply_markup=ikb([[btn(f["name"], f"{action}:{f['id']}")] for f in fields]))


def guard(handler):
    """Menu handlers need a registered user and must reset any half-finished input state."""
    async def wrapper(m: Message, state: FSMContext):
        await state.clear()
        if not registered(m.from_user.id):
            return await m.answer(tr("need_reg", lang_of(m.from_user.id)))
        return await handler(m)
    return wrapper


@dp.message(F.text.in_(labels("m_status")))
@dp.message(Command("status"))
async def menu_status(m: Message, state: FSMContext):
    await guard(lambda mm: choose_field(mm, mm.from_user.id, "fst"))(m, state)


@dp.message(F.text.in_(labels("m_plan")))
@dp.message(Command("plan"))
async def menu_plan(m: Message, state: FSMContext):
    await guard(lambda mm: choose_field(mm, mm.from_user.id, "fpl"))(m, state)


@dp.callback_query(F.data.startswith("fst:"))
async def cb_status(c: CallbackQuery):
    await c.answer()
    await send_status(c.message, c.from_user.id, int(c.data.split(":")[1]))


@dp.callback_query(F.data.startswith("fpl:"))
async def cb_plan(c: CallbackQuery):
    await c.answer()
    await send_plan(c.message, c.from_user.id, int(c.data.split(":")[1]))


# ---------------- my fields (card, edit, delete, alerts) ----------------
def field_card(f: dict, lang: str):
    text = (f"📍 {f['name']}\n{region_name(f['region'], lang)}\n"
            f"🌾 {nm(CROP_NAMES, f['crop'], lang)} · {nm(STAGE_NAMES, f['stage'], lang)}\n"
            f"💧 {nm(GW_NAMES, f['groundwater'], lang)} · {nm(DR_NAMES, f['drainage'], lang)}")
    fid = f["id"]
    kb = ikb([
        [btn(tr("b_status", lang), f"fst:{fid}"), btn(tr("b_plan", lang), f"fpl:{fid}")],
        [btn(tr("b_crop", lang), f"fcrop:{fid}"), btn(tr("b_stage", lang), f"fstg:{fid}")],
        [btn(tr("b_salt", lang), f"fsalt:{fid}")],
        [btn(tr("b_notif_on" if f["notify"] else "b_notif_off", lang), f"fnot:{fid}"), btn(tr("b_delete", lang), f"fdel:{fid}")],
    ])
    return text, kb


@dp.message(F.text.in_(labels("m_fields")))
async def menu_fields(m: Message, state: FSMContext):
    async def run(mm):
        lang = lang_of(mm.from_user.id)
        fields = db.fields_of(mm.from_user.id)
        if not fields:
            return await mm.answer(tr("nofield", lang))
        await mm.answer(tr("fields_title", lang), reply_markup=ikb([[btn(f"📍 {f['name']}", f"fld:{f['id']}")] for f in fields]))
    await guard(run)(m, state)


@dp.callback_query(F.data.startswith("fld:"))
async def cb_field(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    text, kb = field_card(f, lang)
    await c.message.answer(text, reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data.startswith("fcrop:"))
async def cb_change_crop(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    rows = chunk([btn(nm(CROP_NAMES, k, lang), f"setcrop:{f['id']}:{k}") for k in CROPS], 3)
    await c.message.answer(tr("crop_q", lang), reply_markup=ikb(rows))
    await c.answer()


@dp.callback_query(F.data.startswith("setcrop:"))
async def cb_set_crop(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, crop = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or crop not in CROPS:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], crop=crop)
    await c.message.answer(tr("updated", lang))
    await send_status(c.message, c.from_user.id, f["id"])
    await c.answer()


@dp.callback_query(F.data.startswith("fstg:"))
async def cb_change_stage(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    await c.message.answer(tr("stage_q", lang), reply_markup=ikb(
        [[btn(nm(STAGE_NAMES, s, lang), f"setstage:{f['id']}:{s}")] for s in STAGES]))
    await c.answer()


@dp.callback_query(F.data.startswith("setstage:"))
async def cb_set_stage(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    _, fid, stage = c.data.split(":")
    f = own_field(c.from_user.id, fid)
    if not f or stage not in STAGES:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], stage=stage)
    await c.message.answer(tr("updated", lang))
    await send_status(c.message, c.from_user.id, f["id"])
    await c.answer()


@dp.callback_query(F.data.startswith("fsalt:"))
async def cb_salt(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    await ask_gw(c.message, f["id"], lang)
    await c.answer()


@dp.callback_query(F.data.startswith("fnot:"))
async def cb_field_notify(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    db.field_update(f["id"], notify=0 if f["notify"] else 1)
    text, kb = field_card(db.field_get(f["id"]), lang)
    await c.message.edit_reply_markup(reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data.startswith("fdel:"))
async def cb_field_delete(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if not f:
        return await c.answer(tr("field_gone", lang), show_alert=True)
    await c.message.answer(f"{tr('confirm_del', lang)} ({f['name']})", reply_markup=ikb(
        [[btn(tr("b_yes", lang), f"fdely:{f['id']}"), btn(tr("b_no", lang), "noop")]]))
    await c.answer()


@dp.callback_query(F.data.startswith("fdely:"))
async def cb_field_delete_yes(c: CallbackQuery):
    lang = lang_of(c.from_user.id)
    f = own_field(c.from_user.id, c.data.split(":")[1])
    if f:
        db.field_delete(f["id"])
    await c.message.edit_text(tr("deleted", lang))
    await c.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery):
    await c.message.edit_text(tr("cancelled", lang_of(c.from_user.id)))
    await c.answer()


# ---------------- about ----------------
@dp.message(F.text.in_(labels("m_about")))
@dp.message(Command("help"))
async def menu_about(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(tr("about", lang_of(m.from_user.id)))


@dp.message(F.text.in_(labels("m_app")))
@dp.message(Command("app"))
async def cmd_app(m: Message):
    lang = lang_of(m.from_user.id)
    if not app_url():
        logging.warning("WEBAPP_URL (https) is not configured: /app cannot open the Mini App")
        return await m.answer(tr("app_not_set", lang))
    await m.answer(tr("open_app_msg", lang), reply_markup=open_app_kb(lang))


@dp.message(Command("map"))
async def open_map(m: Message):
    lang = lang_of(m.from_user.id)
    if not config.WEBAPP_URL:
        logging.warning("WEBAPP_URL is not configured: /map cannot open")
        return await m.answer(tr("app_not_set", lang))
    await m.answer("🗺", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🗺 " + APP["a_map"].get(lang, APP["a_map"]["en"]), web_app=WebAppInfo(url=config.WEBAPP_URL))]]))


# ---------------- community ----------------
def post_kb(p: dict, uid: int, lang: str, likes: int | None = None) -> InlineKeyboardMarkup:
    n = p.get("likes", 0) if likes is None else likes
    row = [btn(f"{tr('like', lang)} {n}", f"like:{p['id']}")]
    if p["user_id"] == uid:
        row.append(btn(tr("del_post", lang), f"pdel:{p['id']}"))
    else:
        row.append(btn(tr("report", lang), f"rep:{p['id']}"))
    return ikb([row])


async def show_posts(m: Message, posts: list, uid: int, lang: str):
    if not posts:
        return await m.answer(tr("c_none", lang))
    for p in reversed(posts):
        head = f"👤 {p['author']} · {region_name(p['region'], lang)} · {p['created'][:10]}"
        await m.answer(f"{head}\n\n{p['text']}", reply_markup=post_kb(p, uid, lang))


@dp.message(F.text.in_(labels("m_comm")))
async def menu_comm(m: Message, state: FSMContext):
    async def run(mm):
        lang = lang_of(mm.from_user.id)
        await mm.answer(tr("comm_title", lang), reply_markup=ikb([
            [btn(tr("c_region", lang), "cm:region"), btn(tr("c_all", lang), "cm:all")],
            [btn(tr("c_write", lang), "cm:write"), btn(tr("c_mine", lang), "cm:mine")]]))
    await guard(run)(m, state)


@dp.callback_query(F.data.startswith("cm:"))
async def cb_comm(c: CallbackQuery, state: FSMContext):
    uid, lang = c.from_user.id, lang_of(c.from_user.id)
    if not registered(uid):
        return await c.answer(tr("need_reg", lang), show_alert=True)
    act = c.data.split(":")[1]
    await c.answer()
    if act == "write":
        await state.set_state(Post.text)
        return await c.message.answer(tr("ask_post", lang))
    if act == "region":
        posts = db.posts_latest((db.user_get(uid) or {}).get("region"))
    elif act == "all":
        posts = db.posts_latest()
    else:
        posts = db.posts_of(uid)
    await show_posts(c.message, posts, uid, lang)


@dp.message(Post.text, F.text)
async def post_text(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    text = m.text.strip()
    if not 10 <= len(text) <= 500:
        return await m.answer(tr("post_bad", lang))
    if db.posts_today(uid) >= 5:
        await state.clear()
        return await m.answer(tr("post_limit", lang))
    u = db.user_get(uid)
    db.post_add(uid, u["name"] or tr("farmer", lang), u["region"], text)
    await state.clear()
    await m.answer(tr("post_saved", lang), reply_markup=main_menu(lang))


@dp.callback_query(F.data.startswith("like:"))
async def cb_like(c: CallbackQuery):
    uid, lang = c.from_user.id, lang_of(c.from_user.id)
    p = db.post_get(int(c.data.split(":")[1]))
    if not p or p["hidden"] or not registered(uid):
        return await c.answer()
    n = db.like_toggle(p["id"], uid)
    await c.message.edit_reply_markup(reply_markup=post_kb(p, uid, lang, n))
    await c.answer()


@dp.callback_query(F.data.startswith("rep:"))
async def cb_report(c: CallbackQuery):
    uid, lang = c.from_user.id, lang_of(c.from_user.id)
    p = db.post_get(int(c.data.split(":")[1]))
    if not p or not registered(uid):
        return await c.answer()
    new = db.report_post(p["id"], uid)
    await c.answer(tr("reported" if new else "reported_already", lang), show_alert=True)


@dp.callback_query(F.data.startswith("pdel:"))
async def cb_post_delete(c: CallbackQuery):
    uid, lang = c.from_user.id, lang_of(c.from_user.id)
    p = db.post_get(int(c.data.split(":")[1]))
    if p and p["user_id"] == uid:
        db.post_delete(p["id"])
        await c.message.edit_text(tr("deleted", lang))
    await c.answer()


# ---------------- settings ----------------
def settings_kb(uid: int, lang: str) -> InlineKeyboardMarkup:
    u = db.user_get(uid)
    return ikb([[btn(tr("s_lang", lang), "set:lang"), btn(tr("s_region", lang), "set:region")],
                [btn(tr("s_notif_on" if u["notify"] else "s_notif_off", lang), "set:notif")],
                [btn(tr("s_delete", lang), "set:del")]])


@dp.message(F.text.in_(labels("m_set")))
async def menu_settings(m: Message, state: FSMContext):
    async def run(mm):
        lang = lang_of(mm.from_user.id)
        await mm.answer(tr("set_title", lang), reply_markup=settings_kb(mm.from_user.id, lang))
    await guard(run)(m, state)


@dp.callback_query(F.data.startswith("set:"))
async def cb_settings(c: CallbackQuery):
    uid, lang = c.from_user.id, lang_of(c.from_user.id)
    if not registered(uid):
        return await c.answer(tr("need_reg", lang), show_alert=True)
    act = c.data.split(":")[1]
    await c.answer()
    if act == "lang":
        await c.message.answer("🌐", reply_markup=ikb([[btn(t, f"lang:{code}") for t, code in LANG_BUTTONS]]))
    elif act == "region":
        await c.message.answer(tr("ask_region", lang), reply_markup=ikb(region_buttons("rgn", lang)))
    elif act == "notif":
        u = db.user_get(uid)
        db.user_upsert(uid, notify=0 if u["notify"] else 1)
        await c.message.edit_reply_markup(reply_markup=settings_kb(uid, lang))
    elif act == "del":
        await c.message.answer(tr("confirm_acc", lang), reply_markup=ikb(
            [[btn(tr("b_yes", lang), "set:delyes"), btn(tr("b_no", lang), "noop")]]))
    elif act == "delyes":
        db.user_delete(uid)
        await c.message.edit_text(tr("acc_deleted", lang))
        await c.message.answer("👋", reply_markup=ReplyKeyboardRemove())


# ---------------- generic ----------------
@dp.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    lang = lang_of(m.from_user.id)
    await m.answer(tr("cancelled", lang), reply_markup=main_menu(lang) if registered(m.from_user.id) else ReplyKeyboardRemove())


@dp.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext):
    await state.clear()
    lang = lang_of(m.from_user.id)
    if registered(m.from_user.id):
        await m.answer(tr("menu_hint", lang), reply_markup=main_menu(lang))
    else:
        await m.answer(tr("need_reg", lang))


@dp.message()
async def fallback(m: Message):
    if app_url():
        return await app_only(m)
    lang = lang_of(m.from_user.id)
    if registered(m.from_user.id):
        await m.answer(tr("menu_hint", lang), reply_markup=main_menu(lang))
    else:
        await m.answer(tr("need_reg", lang))


# ---------------- morning notifications ----------------
def needs_attention(a: dict) -> bool:
    return a["irrigation"]["status"] != "WAIT" or a["flush"]["status"] == "CONSIDER"


DO_KEY = {"IRRIGATE": "a_do_irrigate", "MONITOR": "a_do_monitor", "WAIT": "a_do_wait"}


def short_alert(a: dict, lang: str) -> str:
    """Morning message for a farmer: the action first, one reason, flushing only if it matters. Details live in the app."""
    st, fl = a["irrigation"]["status"], a["flush"]
    do = APP[DO_KEY[st]].get(lang, APP[DO_KEY[st]]["en"])
    lines = [f"{EMOJI[st]} {msg_t('st_' + st, lang)}: {do}", msg_t(a["irrigation"]["reason_key"], lang, **a["irrigation"]["params"])]
    if fl["status"] == "CONSIDER":
        lines += ["", "🚿 " + msg_t(fl["reason_key"], lang, **fl["params"])]
    lines += ["", APP["a_alert_more"].get(lang, APP["a_alert_more"]["en"])]
    return "\n".join(lines)


def weather_warnings(forecast, lang: str) -> list[str]:
    """Frost and heavy-rain warnings from the next 3 forecast days (thresholds from app/rules.json)."""
    from .messages import t
    out, fc = [], (forecast or [])[:3]
    tmins = [f["tmin"] for f in fc if f.get("tmin") is not None]
    if tmins and min(tmins) <= rule_val("flush_frost_c"):
        out.append(t("alert_frost", lang, t=round(min(tmins))))
    rain = sum(f.get("rain") or 0 for f in fc)
    if rain >= rule_val("flush_rain_mm"):
        out.append(t("alert_rain", lang, mm=round(rain)))
    return out


async def run_alerts(bot: Bot, now: dt.datetime) -> int:
    """Send today's alerts once per field. Returns the number sent. Separate from the loop so it is testable."""
    sent = 0
    today = now.date().isoformat()
    for f in db.fields_for_alerts():
        if f["last_sent"] == today or now.hour < (f.get("alert_hour") or 7):     # each farmer picks the hour (Settings)
            continue
        try:
            ece = f.get("ece")
            ec_class = class_from_ece(ece) if ece is not None else f["ec_class"]
            a = await get_advice(f["lat"], f["lon"], crop=f["crop"], stage=f["stage"], groundwater=f["groundwater"],
                                 drainage=f["drainage"], last_flush_days=db.flush_days(f), ec_class=ec_class,
                                 ece=ece, water_ec=f.get("water_ec"),
                                 since_irrigation=db.last_event_days(f["id"], "irrigated"))
            _, forecast = await get_snapshot(f["lat"], f["lon"])
            warnings = weather_warnings(forecast, f["lang"])
            db.log_advice(f["id"], a, now.date())
            if needs_attention(a) or warnings:
                head = f"{tr('alert_head', f['lang'])}\n📍 {f['name']} — {nm(CROP_NAMES, f['crop'], f['lang'])}\n\n"
                top = "\n".join(warnings) + ("\n\n" if warnings else "")
                await bot.send_message(f["user_id"], head + top + short_alert(a, f["lang"]),
                                       reply_markup=open_app_kb(f["lang"]))
                sent += 1
            db.field_update(f["id"], last_sent=today)
            await asyncio.sleep(0.05)       # stay well under Telegram's rate limits
        except Exception:
            logging.exception("alert failed for field %s", f["id"])
    return sent


async def daily_alerts(bot: Bot):
    while True:
        now = dt.datetime.now(TZ)
        if 5 <= now.hour < 20:
            await run_alerts(bot, now)
        await asyncio.sleep(1800)


BOT: Bot | None = None


async def refresh_menu_button():
    """Blue "Sho'r Radar" button next to the message box opens the Mini App. Called at start and whenever the tunnel address changes."""
    if BOT and app_url():
        for attempt in range(3):
            try:
                await BOT.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Sho'r Radar", web_app=WebAppInfo(url=app_url())))
                return
            except Exception:
                logging.warning("could not set menu button (attempt %s)", attempt + 1)
                await asyncio.sleep(3)


async def main():
    global BOT
    if not config.TELEGRAM_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (see .env.example)")
    logging.basicConfig(level=logging.INFO)
    db.init()
    bot = Bot(config.TELEGRAM_TOKEN)
    BOT = bot
    alerts = None
    try:
        await refresh_menu_button()
        alerts = asyncio.create_task(daily_alerts(bot))
        await dp.start_polling(bot)
    finally:
        if alerts:
            alerts.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
