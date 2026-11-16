"""Offline end-to-end test of the Telegram bot: feeds fake Telegram updates through the real handlers
using a fake HTTP session (no network, no token needed), with demo weather data."""
import asyncio
import datetime as dt
import itertools

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Location, Message, Update, User

from app import bot as botmod, config, db


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self): ...

    async def stream_content(self, *a, **k):
        yield b""

    async def make_request(self, bot, method: TelegramMethod, timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=len(self.calls), date=dt.datetime.now(), chat=Chat(id=method.chat_id, type="private"),
                           text=method.text)
        return True

    def texts(self, uid=None):
        return [m.text for m in self.calls if isinstance(m, SendMessage) and (uid is None or m.chat_id == uid)]


class Harness:
    def __init__(self):
        self.session = FakeSession()
        self.bot = Bot("123456:TEST", session=self.session)
        self.ids = itertools.count(1)

    async def _feed(self, **kw):
        upd = Update(update_id=next(self.ids), **kw)
        await botmod.dp.feed_raw_update(self.bot, upd.model_dump(mode="json", exclude_none=True))

    def _msg(self, uid, **kw):
        return Message(message_id=next(self.ids), date=dt.datetime.now(), chat=Chat(id=uid, type="private"),
                       from_user=User(id=uid, is_bot=False, first_name="T"), **kw)

    async def say(self, uid, text):
        self.session.calls.clear()
        await self._feed(message=self._msg(uid, text=text))
        return self.session.texts(uid)

    async def send_location(self, uid, lat, lon):
        self.session.calls.clear()
        await self._feed(message=self._msg(uid, location=Location(latitude=lat, longitude=lon)))
        return self.session.texts(uid)

    async def press(self, uid, data):
        self.session.calls.clear()
        host = Message(message_id=next(self.ids), date=dt.datetime.now(), chat=Chat(id=uid, type="private"), text="x")
        cq = CallbackQuery(id=str(next(self.ids)), from_user=User(id=uid, is_bot=False, first_name="T"),
                           chat_instance="ci", data=data, message=host)
        await self._feed(callback_query=cq)
        return self.session.texts(uid)


@pytest.fixture()
def h(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init()
    # fresh FSM storage per test
    from aiogram.fsm.storage.memory import MemoryStorage
    botmod.dp.fsm.storage = MemoryStorage()
    return Harness()


async def register(h, uid=1, lang="en"):
    await h.say(uid, "/start")
    await h.press(uid, f"lang:{lang}")
    await h.press(uid, "reg")
    await h.say(uid, "Ali")
    out = await h.press(uid, "rgn:urgench")
    return out


async def add_field(h, uid=1):
    out = await h.say(uid, "North field")
    await h.press(uid, f"floc:{_last_fid(uid)}:urgench")
    fid = _last_fid(uid)
    for step in (f"crop:{fid}:cotton", f"stage:{fid}:mid", f"gw:{fid}:shallow", f"dr:{fid}:good", f"fl:{fid}:gt12"):
        await h.press(uid, step)
    return fid, await h.press(uid, f"ec:{fid}:high")


def _last_fid(uid):
    import sqlite3
    c = sqlite3.connect(config.DB_PATH)
    return c.execute("SELECT MAX(id) FROM fields WHERE user_id=?", (uid,)).fetchone()[0]


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("lang", ["en", "uz", "ru"])
def test_register_field_status_plan(h, lang):
    async def go():
        out = await h.say(1, "/start")
        assert "Sho'r Radar" in out[0]
        out = await h.press(1, f"lang:{lang}")
        assert out and "NASA" in out[0]                         # about text explains the process
        await h.press(1, "reg")
        await h.say(1, "Ali")
        out = await register_rest(h, lang)
        assert db.user_get(1)["registered"] == 1 and db.user_get(1)["region"] == "urgench"
        assert any(botmod.tr("ask_fname", lang) == t for t in out)
        fid, out = await add_field(h)
        f = db.field_get(fid)
        assert (f["crop"], f["stage"], f["groundwater"], f["drainage"], f["last_flush_days"], f["ec_class"]) == \
               ("cotton", "mid", "shallow", "good", 500, "high")
        assert abs(f["lat"] - 41.55) < 0.01
        status = [t for t in out if "North field" in t]
        assert status, out                                       # status message was produced
        out = await h.say(1, botmod.tr("m_plan", lang))
        assert out and "NASA" in out[-1] and "→" in out[-1]      # plan with rotation + disclaimer
        assert len(db.recent_log(fid)) == 1
    run(go())


async def register_rest(h, lang):
    return await h.press(1, "rgn:urgench")


def test_unregistered_user_is_blocked(h):
    async def go():
        out = await h.say(5, botmod.tr("m_status", "uz"))
        assert out == [botmod.tr("need_reg", "uz")]
    run(go())


def test_location_outside_uzbekistan_rejected(h):
    async def go():
        await h.say(1, "/start"); await h.press(1, "lang:en"); await h.press(1, "reg"); await h.say(1, "Ali")
        await h.press(1, "rgn:urgench")
        await h.say(1, "My field")
        out = await h.send_location(1, 48.85, 2.35)             # Paris
        assert out == [botmod.tr("loc_out", "en")]
        out = await h.send_location(1, 40.40, 71.70)            # near Fergana
        assert db.fields_of(1)[0]["region"] == "fergana"
    run(go())


def test_cannot_touch_someone_elses_field(h):
    async def go():
        await register(h, 1)
        fid, _ = await add_field(h, 1)
        await register(h, 2)
        for data in (f"fst:{fid}", f"fpl:{fid}", f"fdely:{fid}", f"setcrop:{fid}:maize", f"fnot:{fid}", f"gw:{fid}:deep"):
            out = await h.press(2, data)
            assert out == [] or all("North field" not in t for t in out), data
        f = db.field_get(fid)
        assert f and f["crop"] == "cotton" and f["groundwater"] == "shallow" and f["notify"] == 1
    run(go())


def test_community_post_like_report_delete(h):
    async def go():
        await register(h, 1); await register(h, 2)
        await h.press(1, "cm:write")
        out = await h.say(1, "short")
        assert out == [botmod.tr("post_bad", "en")]
        await h.say(1, "Flushing in January worked well with working drains in Urgench.")
        assert len(db.posts_latest()) == 1
        out = await h.press(2, "cm:all")
        assert out and "Ali" in out[0] and "Flushing" in out[0]
        pid = db.posts_latest()[0]["id"]
        await h.press(2, f"like:{pid}")
        assert db.posts_latest()[0]["likes"] == 1
        await h.press(2, f"like:{pid}")
        assert db.posts_latest()[0]["likes"] == 0                 # toggle
        await h.press(2, f"pdel:{pid}")                           # not the owner: nothing happens
        assert db.post_get(pid)
        await h.press(1, f"pdel:{pid}")
        assert db.post_get(pid) is None
    run(go())


def test_post_hidden_after_three_reports(h):
    pid = db.post_add(9, "X", "bukhara", "some questionable advice here")
    assert db.report_post(pid, 1) and db.report_post(pid, 2)
    assert not db.report_post(pid, 2)                             # duplicate report ignored
    assert db.posts_latest()
    db.report_post(pid, 3)
    assert db.posts_latest() == []


def test_daily_limit_five_posts(h):
    async def go():
        await register(h, 1)
        for i in range(5):
            db.post_add(1, "Ali", "urgench", f"post number {i} text")
        await h.press(1, "cm:write")
        out = await h.say(1, "this is the sixth post today")
        assert out == [botmod.tr("post_limit", "en")]
    run(go())


def test_alerts_sent_once_per_day(h, monkeypatch):
    async def go():
        await register(h, 1)
        fid, _ = await add_field(h, 1)
        # force an actionable signal regardless of the random demo data
        real = botmod.get_advice

        async def fake(*a, **k):
            adv = await real(*a, **k)
            adv["irrigation"]["status"] = "IRRIGATE"
            return adv
        monkeypatch.setattr(botmod, "get_advice", fake)
        h.session.calls.clear()
        now = dt.datetime(2026, 11, 20, 7, 30)
        assert await botmod.run_alerts(h.bot, now) == 1
        assert botmod.tr("alert_head", "en") in h.session.texts(1)[0]
        assert await botmod.run_alerts(h.bot, now) == 0           # same day: no duplicate
        assert await botmod.run_alerts(h.bot, now + dt.timedelta(days=1)) == 1
        db.field_update(fid, notify=0)
        assert await botmod.run_alerts(h.bot, now + dt.timedelta(days=2)) == 0   # alerts off
    run(go())


def test_delete_account_removes_everything(h):
    async def go():
        await register(h, 1)
        fid, _ = await add_field(h, 1)
        db.post_add(1, "Ali", "urgench", "my post that will be removed")
        await h.press(1, "set:del")
        await h.press(1, "set:delyes")
        assert db.user_get(1) is None and db.field_get(fid) is None and db.posts_latest() == []
    run(go())


def test_app_only_mode_shows_single_open_app_button(h, monkeypatch):
    monkeypatch.setattr(config, "WEBAPP_URL", "https://example.trycloudflare.com")

    async def go():
        for text in ("/start", "hello", "📊 Status"):
            await h.say(7, text)
            msgs = [m for m in h.session.calls if isinstance(m, SendMessage)]
            assert len(msgs) == 2
            assert type(msgs[0].reply_markup).__name__ == "ReplyKeyboardRemove"       # old bottom keyboard removed
            btn = msgs[1].reply_markup.inline_keyboard[0][0]
            assert btn.web_app.url == "https://example.trycloudflare.com/app"
    run(go())
