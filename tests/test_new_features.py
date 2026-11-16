"""Measured salinity, water EC, rules table + decision trace, disk cache fallback, weather alerts, verified badge."""
import asyncio
import datetime as dt
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import bot as botmod, config, db, rules
from app.data import nasa_power
from app.data.demo import demo_forecast, demo_power
from app.engine.crops import class_from_ece, recommend
from app.engine.flush import flush_guidance
from app.engine.irrigation import irrigation_advice
from app.engine.trace import irrigation_trace
from tests.test_webapp_api import H, TOKEN, client, reg  # noqa: F401  (fixtures/helpers)


# ---------- measured ECe ----------
def test_class_from_ece_uses_fao_bounds():
    assert [class_from_ece(x) for x in (0, 3.9, 4, 7.9, 8, 20)] == ["low", "low", "medium", "medium", "high", "high"]


def test_measured_ece_overrides_weather_level_and_decides_crop_fit():
    r = recommend("HIGH", None, ece=1.0)                  # weather says HIGH risk, the measurement says clean soil
    assert r["level"] == "LOW" and r["assumed_ec"] == 1.0
    assert next(c for c in r["crops"] if c["crop"] == "onion")["fit"] == "good"        # onion threshold 1.2 dS/m
    r = recommend("LOW", None, ece=9.0)
    assert r["level"] == "HIGH" and next(c for c in r["crops"] if c["crop"] == "rice")["fit"] == "avoid"
    assert next(c for c in r["crops"] if c["crop"] == "barley")["fit"] == "marginal"   # barley tolerates 8.0 dS/m, the soil is at 9.0
    # a farmer's low/medium/high guess can only raise the level, never lower it
    assert recommend("HIGH", "low")["level"] == "HIGH" and recommend("LOW", "high")["level"] == "HIGH"


def test_api_ece_roundtrip_validation_stale_and_clear(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus", "ece": 9.5}).json()["id"]
    f = client.get("/api/app/bootstrap", headers=H()).json()["fields"][0]
    assert f["ece"] == 9.5 and f["ece_date"] == dt.date.today().isoformat() and f["ec_class"] == "high"
    s = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()
    assert s["salt_measured"] is True and s["measurement"]["ece_class"] == 3 and s["measurement"]["stale"] is False   # strongly saline (8-16)
    c = client.get(f"/api/app/fields/{fid}/crops", headers=H()).json()
    assert c["ec_known"] is True and c["level"] == "HIGH" and c["assumed_ec"] == 9.5
    assert {x["crop"]: x["fit"] for x in c["crops"]}["rice"] == "avoid"
    old = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    client.put(f"/api/app/fields/{fid}", headers=H(), json={"ece": 3.0, "ece_date": old})
    assert client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["measurement"]["stale"] is True
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"ece": -1}).status_code == 422
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"ece": 3, "ece_date": "2999-01-01"}).status_code == 422
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"ece": 3, "ece_date": "not-a-date"}).status_code == 422
    client.put(f"/api/app/fields/{fid}", headers=H(), json={"clear_ece": True})
    s = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()
    assert s["salt_measured"] is False and s["measurement"]["ece"] is None


# ---------- irrigation-water EC ----------
def test_saline_irrigation_water_blocks_flushing_advice():
    series, fc = demo_power(41.5, 60.6), [{"date": dt.date.today(), "rain": 0, "tmax": 8, "tmin": 3}] * 3
    ok = flush_guidance(series, fc, "HIGH", "good", 41.5, water_ec=1.0)
    bad = flush_guidance(series, fc, "HIGH", "good", 41.5, water_ec=3.5)
    assert bad["status"] == "NOT_ADVISED" and bad["reason_key"] == "flush_saline_water" and bad["params"]["ec"] == 3.5
    assert ok["reason_key"] != "flush_saline_water"
    assert flush_guidance(series, fc, "LOW", "good", 41.5, water_ec=9)["status"] == "NOT_NEEDED"      # low salt risk: nothing to flush anyway


def test_api_water_ec_class_in_status(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus", "water_ec": 3.4}).json()["id"]
    m = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["measurement"]
    assert m["water_ec"] == 3.4 and m["water_class"] == 2                      # severe restriction (> 3 dS/m)
    client.put(f"/api/app/fields/{fid}", headers=H(), json={"water_ec": 0.5})
    assert client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["measurement"]["water_class"] == 0


# ---------- rules table + decision trace ----------
def test_rules_table_is_complete_and_honest():
    t = rules.table("uz")
    assert t["validated_by"] is None and t["version"]
    assert all(set(r["label"]) for r in t["rules"]) and len(t["rules"]) >= 15
    assert all(rules.RULES[k]["label"].keys() >= {"en", "uz", "ru"} for k in rules.RULES)
    for k in ("dry_wetness", "watch_wetness", "max_deficit_mm", "wait_rain_mm", "flush_frost_c", "flush_rain_mm", "water_ec_limit", "ece_med"):
        assert k in rules.RULES
    assert next(r for r in t["rules"] if r["id"] == "dry_wetness")["validated"] is False       # placeholder stays labelled illustrative
    assert next(r for r in t["rules"] if r["id"] == "water_ec_limit")["validated"] is True      # FAO-referenced


def test_trace_always_agrees_with_the_irrigation_signal():
    for lat, lon in [(41.5, 60.6), (42.4, 59.6), (39.8, 64.4), (40.5, 68.8), (40.4, 71.8), (38.0, 66.0), (43.0, 58.0)]:
        series = demo_power(lat, lon)
        for rain_fc in (0.0, 2.0, 12.0):
            fc = [{"date": dt.date.today(), "rain": rain_fc / 3, "tmax": 20, "tmin": 8}] * 7
            for forecast in (fc, None):
                for stage in ("initial", "mid", "late"):
                    adv = irrigation_advice(series, forecast, "cotton", stage, lat)
                    tr = irrigation_trace(adv["metrics"], adv["status"], "en")
                    expected = tr["rows"][tr["decisive"]]["outcome"] if tr["decisive"] is not None else "WAIT"
                    assert expected == adv["status"], (lat, rain_fc, stage, tr)
    assert irrigation_trace({}, "WAIT") is None                      # fallow: nothing to explain


def test_changing_a_rule_changes_the_decision(monkeypatch):
    series = demo_power(41.5, 60.6)
    fc = [{"date": dt.date.today(), "rain": 3.0, "tmax": 20, "tmin": 8}] * 7           # 9 mm in the next 3 days
    adv = irrigation_advice(series, fc, "cotton", "mid", 41.5)
    assert adv["status"] == "WAIT" and adv["reason_key"] == "irr_rain"                   # 9 mm >= 8 mm default
    monkeypatch.setitem(rules.RULES["wait_rain_mm"], "value", 50)
    adv = irrigation_advice(series, fc, "cotton", "mid", 41.5)
    assert adv["reason_key"] != "irr_rain"                                               # 9 mm is no longer enough to wait
    assert not next(r for r in irrigation_trace(adv["metrics"], adv["status"])["rows"] if r["id"] == "wait_rain_mm")["hit"]


def test_status_has_trace_and_rules_endpoints(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus"}).json()["id"]
    s = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()
    assert s["rules"]["validated_by"] is None and s["trace"]["rows"] and s["trace"]["outcome"] == s["advice"]["irrigation"]["status"]
    r = client.get("/api/app/rules", headers=H()).json()
    assert r["version"] and any(x["id"] == "dry_wetness" for x in r["rules"])
    src = client.get("/api/app/sources", headers=H()).json()
    assert [x["name"] for x in src][:2] == ["NASA POWER", "Open-Meteo"] and src[0]["resolution"]
    assert client.get("/api/app/rules").status_code == 401 and client.get("/api/app/sources").status_code == 401


# ---------- disk cache: survive NASA outages and restarts ----------
def _power_json():
    days = {"20260101": 1.0, "20260102": 2.0}
    return {"header": {"api": {"version": "v-test-1"}}, "properties": {"parameter": {"T2M": days, "T2M_MAX": days, "T2M_MIN": days}}}


def test_nasa_outage_serves_disk_copy_and_marks_it_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))

    async def no_sleep(_):
        return None
    monkeypatch.setattr(nasa_power.asyncio, "sleep", no_sleep)
    nasa_power._CACHE.clear()

    async def go():
        ok = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=_power_json())))
        rows = await nasa_power.fetch_power(41.5, 60.6, days=30, client=ok)
        assert len(rows) == 2 and nasa_power.META["api_version"] == "v-test-1" and nasa_power.META["stale_used"] is False
        assert list(tmp_path.glob("power_*.json"))                          # a copy was written to disk

        nasa_power._CACHE.clear()                                            # "server restarted"

        def down(req):
            raise httpx.ConnectError("NASA unreachable")
        bad = httpx.AsyncClient(transport=httpx.MockTransport(down))
        rows2 = await nasa_power.fetch_power(41.5, 60.6, days=30, client=bad)
        assert [r["date"] for r in rows2] == [r["date"] for r in rows] and nasa_power.META["stale_used"] is True

        other = await asyncio.gather(nasa_power.fetch_power(10.0, 10.0, days=30, client=bad), return_exceptions=True)
        assert isinstance(other[0], Exception)                               # no copy for a place we never fetched: honest error
    asyncio.run(go())
    nasa_power._CACHE.clear()
    nasa_power.META["stale_used"] = False


# ---------- alerts ----------
class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append((chat_id, text))


@pytest.fixture()
def alert_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "DEMO_MODE", True)
    db.init()
    db.user_upsert(1, lang="en", name="Ali", region="nukus", registered=1)
    fid = db.field_add(1, "North", "nukus")
    db.field_update(fid, lat=42.46, lon=59.61, crop="cotton", stage="mid")

    real = botmod.get_advice

    async def forced(*a, **k):
        adv = await real(*a, **k)
        adv["irrigation"]["status"] = "WAIT"
        adv["flush"]["status"] = "NOT_NOW"           # nothing actionable: only weather can trigger a message
        return adv
    monkeypatch.setattr(botmod, "get_advice", forced)
    return fid


def test_weather_warnings_use_rules_table():
    cold = [{"tmin": -6, "rain": 0}, {"tmin": 1, "rain": 0}, {"tmin": 2, "rain": 0}]
    wet = [{"tmin": 5, "rain": 9}, {"tmin": 5, "rain": 9}, {"tmin": 5, "rain": 0}]
    assert "❄️" in botmod.weather_warnings(cold, "en")[0] and "-6" in botmod.weather_warnings(cold, "en")[0]
    assert "🌧" in botmod.weather_warnings(wet, "en")[0] and "18" in botmod.weather_warnings(wet, "en")[0]
    assert botmod.weather_warnings([{"tmin": 5, "rain": 1}] * 3, "en") == [] and botmod.weather_warnings(None, "en") == []
    assert "Заморозки" in botmod.weather_warnings(cold, "ru")[0] or "заморозки" in botmod.weather_warnings(cold, "ru")[0]


def test_alert_only_when_weather_warrants_and_respects_chosen_hour(alert_env, monkeypatch):
    async def go():
        bot = FakeBot()
        calm = [{"date": dt.date.today(), "rain": 0, "tmax": 15, "tmin": 4}] * 7
        frosty = [{"date": dt.date.today(), "rain": 0, "tmax": 5, "tmin": -7}] * 7

        async def snap_calm(*a, **k):
            return demo_power(42.46, 59.61), calm

        async def snap_frost(*a, **k):
            return demo_power(42.46, 59.61), frosty
        now = dt.datetime(2026, 11, 20, 8, 0)

        monkeypatch.setattr(botmod, "get_snapshot", snap_calm)
        assert await botmod.run_alerts(bot, now) == 0 and bot.sent == []              # nothing actionable and calm weather: silence

        db.field_update(alert_env, last_sent=None)
        monkeypatch.setattr(botmod, "get_snapshot", snap_frost)
        db.user_upsert(1, alert_hour=9)
        assert await botmod.run_alerts(bot, now) == 0                                  # it is 08:00 but this farmer chose 09:00
        db.user_upsert(1, alert_hour=8)
        assert await botmod.run_alerts(bot, now) == 1
        assert "❄️" in bot.sent[0][1] and "North" in bot.sent[0][1]
        assert await botmod.run_alerts(bot, now) == 0                                  # once per day
    asyncio.run(go())


def test_alert_hour_setting_is_validated(client):
    reg(client)
    assert client.post("/api/app/settings", headers=H(), json={"alert_hour": 9}).status_code == 200
    assert client.get("/api/app/bootstrap", headers=H()).json()["user"]["alert_hour"] == 9
    for bad in (4, 11, 25):
        assert client.post("/api/app/settings", headers=H(), json={"alert_hour": bad}).status_code == 422


# ---------- verified agronomist badge ----------
def test_verified_badge_only_for_agronomists(client):
    reg(client, 1); reg(client, 2)
    client.post("/api/app/posts", headers=H(1), json={"text": "Leach in January when the drains run well."})
    client.post("/api/app/posts", headers=H(2), json={"text": "My cotton did fine with less water this year."})
    db.user_upsert(1, role="agronomist")
    posts = {p["author"]: p for p in client.get("/api/app/posts?scope=all", headers=H(2)).json()}
    assert posts["U1"]["verified"] is True and posts["U2"]["verified"] is False
    assert client.get("/api/app/bootstrap", headers=H(1)).json()["user"]["role"] == "agronomist"
    # users cannot give themselves the badge through the API
    assert client.post("/api/app/settings", headers=H(2), json={"role": "agronomist"}).status_code == 200
    assert db.user_get(2)["role"] != "agronomist"


def test_old_users_table_is_migrated(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.executescript("CREATE TABLE users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz', name TEXT, region TEXT, notify INTEGER DEFAULT 1, registered INTEGER DEFAULT 0, created TEXT);"
                    "INSERT INTO users (user_id, name, registered) VALUES (7, 'Old', 1);")
    c.commit(); c.close()
    monkeypatch.setattr(config, "DB_PATH", str(path))
    db.init()
    u = db.user_get(7)
    assert u["name"] == "Old" and u["alert_hour"] == 7 and u["role"] == "farmer"


# ---------- logged irrigation changes the advice ----------
def test_logged_irrigation_holds_the_signal_and_resets_the_deficit():
    series = demo_power(41.5, 60.6)
    for r in series[-10:]:
        r["PRECTOTCORR"] = 0.0                                   # dry spell
        r["GWETROOT"] = 0.20                                     # model says dry soil (it cannot see irrigation)
    base = irrigation_advice(series, None, "cotton", "mid", 41.5)
    assert base["status"] == "IRRIGATE"
    for days in (0, 2, 4):
        a = irrigation_advice(series, None, "cotton", "mid", 41.5, since_irrigation=days)
        assert a["status"] == "WAIT" and a["reason_key"] == "irr_recent" and a["params"]["n"] == days
        tr = irrigation_trace(a["metrics"], a["status"])
        assert tr["rows"][tr["decisive"]]["id"] == "irrigation_hold_days"
    after_hold = irrigation_advice(series, None, "cotton", "mid", 41.5, since_irrigation=5)
    assert after_hold["metrics"]["deficit_mm"] < base["metrics"]["deficit_mm"]          # counts only 5 days of water use, not 7
    assert irrigation_advice(series, None, "cotton", "mid", 41.5, since_irrigation=30)["metrics"]["deficit_mm"] == base["metrics"]["deficit_mm"]


def test_last_event_days(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    db.init()
    fid = db.field_add(1, "F")
    assert db.last_event_days(fid, "irrigated") is None
    db.event_add(fid, "irrigated", dt.date.today() - dt.timedelta(days=6))
    db.event_add(fid, "irrigated", dt.date.today() - dt.timedelta(days=2))
    db.event_add(fid, "flushed", dt.date.today())
    assert db.last_event_days(fid, "irrigated") == 2 and db.last_event_days(fid, "flushed") == 0


def test_api_irrigation_log_drives_the_status(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus"}).json()["id"]
    assert client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["advice"]["irrigation"]["metrics"]["days_since_irrigation"] is None
    client.post(f"/api/app/fields/{fid}/events", headers=H(), json={"kind": "irrigated"})
    s = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()
    assert s["advice"]["irrigation"]["status"] == "WAIT" and s["advice"]["irrigation"]["reason_key"] == "irr_recent"
    assert s["advice"]["irrigation"]["metrics"]["days_since_irrigation"] == 0
    assert s["trace"]["rows"][s["trace"]["decisive"]]["id"] == "irrigation_hold_days"
    assert "irrigation" in s["text"]["irrigation_reason"].lower() or "sug" in s["text"]["irrigation_reason"].lower()


# ---------- hosting readiness ----------
def test_open_demo_endpoints_are_rate_limited_but_the_app_is_not(client):
    from app import main
    main._HITS.clear()
    url = "/api/advice?lat=41.5&lon=60.6&demo=true"
    codes = [client.get(url).status_code for _ in range(main.OPEN_LIMIT + 3)]
    assert codes[:main.OPEN_LIMIT] == [200] * main.OPEN_LIMIT and codes[main.OPEN_LIMIT:] == [429] * 3
    assert client.get("/api/health").status_code == 200 and client.get("/app").status_code == 200       # unaffected
    assert client.get("/api/advice?lat=41.5&lon=60.6&demo=true", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 200   # per-IP
    main._HITS.clear()
