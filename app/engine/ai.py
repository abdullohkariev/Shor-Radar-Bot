"""Optional Gemini helper. It only EXPLAINS what the rule engine already decided; it never changes a decision.
Cheap by design: smallest model, short prompt, ~350 output tokens, per-user daily limit, answers cached for a day."""
import datetime as dt

import httpx

from .. import config

LANG_NAME = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}
MAX_Q = 300
_cache: dict = {}     # (key) -> answer (per server instance; the limits below live in the database)


class AIError(Exception):
    pass


class AILimit(AIError):
    pass


def enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def build_context(payload: dict) -> str:
    """Compact facts from the rule engine's output (no names, no Telegram ids)."""
    a, tx, m = payload["advice"], payload["text"], payload["measurement"]
    im = a["irrigation"].get("metrics") or {}
    missing = [x for x, v in (("soil salinity (EC) measurement", m.get("ece")), ("irrigation water EC", m.get("water_ec"))) if v is None]
    lines = [
        f"Crop: {a['crop']}, stage: {a['stage']}. Data: {a['data']['source']}, latest {a['data']['last_date']}.",
        f"Irrigation: {tx['irrigation_status']} - {tx['irrigation_reason']}",
        f"Root-zone wetness: {im.get('root_wetness')}, water deficit mm: {im.get('deficit_mm')}, rain next 3 days mm: {im.get('rain_next3d_mm')}",
        f"Salinity risk: {tx['salt_level']} (because: {tx.get('salt_factors')})",
        f"Flushing: {tx['flush_status']} - {tx['flush_reason']}",
        f"Suitable crops now: {', '.join(tx['good_crops'])}",
        f"Missing measurements: {', '.join(missing) if missing else 'none'}",
    ]
    return "\n".join(lines)


def _system(lang: str) -> str:
    return (f"You are the assistant in Sho'r Radar, an advisory app for farmers on saline soils in Uzbekistan. "
            f"Answer ONLY in {LANG_NAME.get(lang, 'English')}, in simple words, max 5 short sentences. "
            "Use ONLY the facts provided. Never change or contradict the app's decision (irrigate/wait/flush). "
            "If the answer needs a measurement that is missing, or something not in the facts, say so and suggest measuring it. "
            "Do not invent numbers. This is advice, not a guarantee.")


def _limit(uid: int) -> None:
    """Per-farmer and global daily limits, stored in the local database (counts only, never the questions)."""
    from .. import db
    if db.assistant_used_today(uid) >= config.AI_DAILY_LIMIT:
        raise AILimit("limit")
    if db.assistant_total_today() >= config.AI_GLOBAL_LIMIT:
        raise AILimit("busy")
    db.assistant_record(uid)


async def ask(uid: int, fid, lang: str, payload: dict, question: str = "") -> str:
    if not enabled():
        raise AIError("disabled")
    question = (question or "").strip()[:MAX_Q]
    ctx = build_context(payload)
    ck = (fid, lang, question, ctx)
    if ck in _cache:
        return _cache[ck]
    _limit(uid)
    q = question or "Explain this advice for my field in simple words and tell me what to do first."
    body = {
        "systemInstruction": {"parts": [{"text": _system(lang)}]},
        "contents": [{"role": "user", "parts": [{"text": f"FACTS:\n{ctx}\n\nQUESTION: {q}"}]}],
        "generationConfig": {"maxOutputTokens": 350, "temperature": 0.3},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY})
        r.raise_for_status()
        text = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]).strip()
    except Exception as e:
        raise AIError(type(e).__name__)
    if not text:
        raise AIError("empty")
    if len(_cache) > 500:
        _cache.clear()
    _cache[ck] = text
    return text
