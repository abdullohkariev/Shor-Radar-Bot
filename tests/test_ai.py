"""'Ask AI' (Gemini): explains the rule engine's advice, never changes it. Limits live in the database."""
import asyncio
import datetime as dt

import aiogram
import pytest
from aiogram.methods import SendMessage

from app import config, db
from app.engine import ai
from tests.test_bot_flow import FakeSession
from tests.test_webapp_api import H, TOKEN, client, reg  # noqa: F401

PAYLOAD = {
    "advice": {"crop": "cotton", "stage": "mid", "data": {"source": "demo", "last_date": "2026-07-01"},
               "irrigation": {"metrics": {"root_wetness": 0.2, "deficit_mm": 30, "rain_next3d_mm": 0}}},
    "text": {"irrigation_status": "Irrigate", "irrigation_reason": "Soil is dry.", "salt_level": "High", "salt_factors": "shallow groundwater",
             "flush_status": "Wait", "flush_reason": "No drainage.", "good_crops": ["wheat"]},
    "measurement": {"ece": None, "water_ec": None},
}

def update(text="/start", uid=77):
    return {"update_id": 1, "message": {"message_id": 5, "date": int(dt.datetime.now().timestamp()), "chat": {"id": uid, "type": "private"},
                                        "from": {"id": uid, "is_bot": False, "first_name": "Ali"}, "text": text}}



class FakeGemini:
    """Replaces httpx.AsyncClient inside app.engine.ai."""
    def __init__(self, text="Plain answer.", status=200):
        self.text, self.status, self.calls, self.bodies = text, status, 0, []

    def install(self, monkeypatch):
        outer = self

        class R:
            def raise_for_status(self):
                if outer.status >= 400:
                    raise RuntimeError(f"HTTP {outer.status}")

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": outer.text}]}}]}

        class C:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

            async def post(self, url, json=None, headers=None):
                outer.calls += 1
                outer.bodies.append(json)
                return R()
        monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **k: C())
        return self


@pytest.fixture()
def gemini(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    db.init()
    ai._cache.clear()
    return FakeGemini().install(monkeypatch)


def test_context_lists_missing_measurements_and_no_ids():
    c = ai.build_context(PAYLOAD)
    assert "soil salinity (EC) measurement" in c and "Irrigate" in c


def test_disabled_without_key(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(ai.AIError):
        asyncio.run(ai.ask(1, 1, "en", PAYLOAD))


def test_daily_limit_cache_and_global_cap(monkeypatch, gemini):
    monkeypatch.setattr(config, "AI_DAILY_LIMIT", 3)
    assert asyncio.run(ai.ask(1, 1, "en", PAYLOAD, "why?")) == "Plain answer."
    assert asyncio.run(ai.ask(1, 1, "en", PAYLOAD, "why?")) == "Plain answer."
    assert gemini.calls == 1                                            # second answer came from the cache: no cost, not counted
    asyncio.run(ai.ask(1, 1, "en", PAYLOAD, "q2"))
    asyncio.run(ai.ask(1, 1, "en", PAYLOAD, "q3"))
    ai._cache.clear()                                                   # a different serverless instance has an empty cache...
    with pytest.raises(ai.AILimit):                                     # ...but the limit is in the database, so it still applies
        asyncio.run(ai.ask(1, 1, "en", PAYLOAD, "one more"))
    assert asyncio.run(ai.ask(2, 1, "en", PAYLOAD, "other farmer")) == "Plain answer."       # limits are per farmer
    monkeypatch.setattr(config, "AI_GLOBAL_LIMIT", db.assistant_total_today())
    with pytest.raises(ai.AILimit):
        asyncio.run(ai.ask(3, 1, "en", PAYLOAD, "global cap reached"))


def test_prompt_contains_facts_and_language_but_no_identity(gemini):
    asyncio.run(ai.ask(42, 7, "uz", PAYLOAD, "Nega?"))
    body = gemini.bodies[0]
    sys_text, user_text = body["systemInstruction"]["parts"][0]["text"], body["contents"][0]["parts"][0]["text"]
    assert "Uzbek" in sys_text and "Never change or contradict" in sys_text
    assert "Soil is dry." in user_text and "Nega?" in user_text
    assert "42" not in user_text and "42" not in sys_text                            # the Telegram id is never sent


# ---------- Mini App endpoints ----------
def test_bootstrap_reports_whether_ai_is_on(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert client.get("/api/app/bootstrap", headers=H()).json()["meta"]["ai"] is False
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    assert client.get("/api/app/bootstrap", headers=H()).json()["meta"]["ai"] is True


def test_field_and_district_ask_answer_with_ai(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    ai._cache.clear()
    g = FakeGemini("Explained simply.").install(monkeypatch)
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus"}).json()["id"]
    r = client.post(f"/api/app/fields/{fid}/ask", headers=H(), json={"question": "Why this advice?"}).json()
    assert r == {"answer": "Explained simply.", "ai": True}
    r = client.post("/api/app/area/bukhara/ask", headers=H(), json={"question": "Should I irrigate?"}).json()
    assert r["ai"] is True and g.calls == 2
    assert client.post("/api/app/area/atlantis/ask", headers=H(), json={"question": "x"}).status_code == 404
    assert client.post(f"/api/app/fields/{fid}/ask", json={"question": "x"}).status_code == 401           # login required


def test_ask_falls_back_to_the_rule_text_when_gemini_fails(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    ai._cache.clear()
    FakeGemini(status=500).install(monkeypatch)
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus"}).json()["id"]
    r = client.post(f"/api/app/fields/{fid}/ask", headers=H(), json={"question": "Why?"}).json()
    assert r["ai"] is False and r["answer"]                    # the app's own explanation, so the farmer still gets something


def test_ask_limit_returns_429_and_other_farmers_unaffected(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(config, "AI_DAILY_LIMIT", 2)
    ai._cache.clear()
    FakeGemini().install(monkeypatch)
    reg(client, 1); reg(client, 2)
    f1 = client.post("/api/app/fields", headers=H(1), json={"name": "A", "region": "nukus"}).json()["id"]
    f2 = client.post("/api/app/fields", headers=H(2), json={"name": "B", "region": "nukus"}).json()["id"]
    codes = [client.post(f"/api/app/fields/{f1}/ask", headers=H(1), json={"question": f"q{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]
    assert client.post(f"/api/app/fields/{f2}/ask", headers=H(2), json={"question": "q"}).status_code == 200
    assert client.post(f"/api/app/fields/{f1}/ask", headers=H(2), json={"question": "q"}).status_code == 404     # not your field


# ---------- the bot ----------
@pytest.fixture()
def bot_env(client, monkeypatch):
    monkeypatch.setattr(config, "WEBAPP_URL", "https://shor.example.app")
    session = FakeSession()
    real = aiogram.Bot
    monkeypatch.setattr(aiogram, "Bot", lambda token, **k: real(token, session=session))
    ai._cache.clear()
    return client, session


def send(client, text, uid=1):
    """Feed one Telegram update straight into the bot's dispatcher (the same path polling uses)."""
    import asyncio
    import types
    from aiogram.types import Update
    from app import bot as botmod

    async def go():
        b = aiogram.Bot("1:test")                      # patched in bot_env: records calls instead of reaching Telegram
        try:
            await botmod.dp.feed_update(b, Update.model_validate(update(text, uid), context={"bot": b}))
        finally:
            await b.session.close()
    asyncio.run(go())
    return types.SimpleNamespace(status_code=200)


def test_bot_answers_typed_questions_with_ai_for_registered_farmers(bot_env, monkeypatch):
    client, session = bot_env
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    FakeGemini("Short answer for the farmer.").install(monkeypatch)
    reg(client)
    client.post("/api/app/fields", headers=H(), json={"name": "North field", "region": "nukus"})
    assert send(client, "Why should I irrigate my north field?").status_code == 200
    msgs = [m for m in session.calls if isinstance(m, SendMessage)]
    assert len(msgs) == 1 and "Short answer for the farmer." in msgs[0].text and "North field" in msgs[0].text
    assert msgs[0].reply_markup.inline_keyboard[0][0].web_app.url == "https://shor.example.app/app"       # app button always offered


def test_bot_uses_the_named_field_and_district_when_there_is_none(bot_env, monkeypatch):
    client, session = bot_env
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    g = FakeGemini("ok").install(monkeypatch)
    reg(client, region="bukhara")
    send(client, "How is my crop doing? (no field yet)")
    assert g.calls == 1 and "📍" not in [m for m in session.calls if isinstance(m, SendMessage)][0].text      # district answer: no field header


def test_bot_keeps_the_open_app_button_when_ai_is_off_or_user_unregistered(bot_env, monkeypatch):
    client, session = bot_env
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    reg(client)
    send(client, "Why irrigate?")
    assert len([m for m in session.calls if isinstance(m, SendMessage)]) == 2          # the old two-message "Open app" reply
    session.calls.clear()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    FakeGemini().install(monkeypatch)
    send(client, "Why irrigate?", uid=555)                                              # never registered: no AI, no data to ground it
    assert len([m for m in session.calls if isinstance(m, SendMessage)]) == 2
    session.calls.clear()
    send(client, "📊 Status")                                                            # old keyboard label is not a question
    assert len([m for m in session.calls if isinstance(m, SendMessage)]) == 2


def test_bot_answer_falls_back_to_rule_text_and_respects_the_limit(bot_env, monkeypatch):
    client, session = bot_env
    monkeypatch.setattr(config, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(config, "AI_DAILY_LIMIT", 1)
    FakeGemini(status=500).install(monkeypatch)
    reg(client)
    send(client, "why?")
    first = [m for m in session.calls if isinstance(m, SendMessage)][0].text
    assert "🤖" not in first and len(first) > 10                                       # Gemini failed: the app's own explanation, no AI note
    session.calls.clear()
    send(client, "and now?")
    second = [m for m in session.calls if isinstance(m, SendMessage)][0].text
    assert "limit" in second.lower() or "limiti" in second.lower() or "лимит" in second.lower()
