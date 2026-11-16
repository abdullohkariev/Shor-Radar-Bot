"""Mini App API: Telegram initData verification and the main endpoints (demo weather data, temp DB)."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.webapp_api import validate_init_data

TOKEN = "123456:TEST-TOKEN"


def make_init(uid=1, token=TOKEN, age=0, name="Ali"):
    data = {"auth_date": str(int(time.time()) - age), "query_id": "AAH",
            "user": json.dumps({"id": uid, "first_name": name}, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "TELEGRAM_TOKEN", TOKEN)
    from app.main import app
    db.init()
    return TestClient(app)


def H(uid=1, **kw):
    return {"X-Init-Data": make_init(uid, **kw)}


def test_init_data_validation():
    assert validate_init_data(make_init(42), TOKEN) == 42
    with pytest.raises(ValueError):
        validate_init_data(make_init(42), "999:OTHER")            # wrong bot token
    with pytest.raises(ValueError):
        validate_init_data(make_init(42, age=90000), TOKEN)       # too old
    tampered = make_init(42).replace("%22id%22%3A42", "%22id%22%3A43")
    with pytest.raises(ValueError):
        validate_init_data(tampered, TOKEN)                       # user id changed
    with pytest.raises(ValueError):
        validate_init_data("", TOKEN)


def test_requires_valid_telegram_login(client):
    assert client.get("/api/app/bootstrap").status_code == 401
    assert client.get("/api/app/bootstrap", headers={"X-Init-Data": "hash=bad"}).status_code == 401
    assert client.get("/api/app/bootstrap", headers=H()).status_code == 200


def test_register_field_status_plan_flow(client):
    b = client.get("/api/app/bootstrap", headers=H()).json()
    assert b["user"]["registered"] is False and "about" in b["i18n"] and len(b["meta"]["regions"]) == 14
    assert client.post("/api/app/fields", headers=H(), json={"name": "x", "region": "urgench"}).status_code == 403   # must register first
    r = client.post("/api/app/register", headers=H(), json={"name": "Ali", "region": "urgench", "lang": "ru"})
    assert r.status_code == 200
    f = client.post("/api/app/fields", headers=H(), json={
        "name": "North", "region": "urgench", "crop": "cotton", "stage": "mid", "groundwater": "shallow",
        "drainage": "good", "last_flush": "gt12", "ec": "high"})
    assert f.status_code == 200, f.text
    fid = f.json()["id"]
    assert f.json()["ec"] == "high" and f.json()["last_flush"] == "gt12"
    s = client.get(f"/api/app/fields/{fid}/status", headers=H()).json()
    assert s["advice"]["irrigation"]["status"] in ("IRRIGATE", "MONITOR", "WAIT")
    assert s["text"]["irrigation_status"] and s["text"]["good_crops"] and s["salt_measured"] is False      # a low/medium/high guess is not a measurement
    assert any(c in s["text"]["good_crops"] for c in ("Ячмень", "Хлопчатник"))           # localized crop names
    p = client.get(f"/api/app/fields/{fid}/plan", headers=H()).json()
    assert p["outlook"] and len(p["rotation"]) == 3 and "NASA" in p["disclaimer"]
    up = client.put(f"/api/app/fields/{fid}", headers=H(), json={"crop": "wheat", "ec": "unk"}).json()
    assert up["crop"] == "wheat" and up["ec"] == "unk"
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"crop": "bananas"}).status_code == 422
    assert client.post("/api/app/fields", headers=H(), json={"name": "Far", "lat": 48.8, "lon": 2.3}).status_code == 422
    assert client.post("/api/app/fields", headers=H(), json={"name": "GPS", "lat": 40.4, "lon": 71.7}).json()["region"] == "fergana"


def test_cannot_access_other_users_data(client):
    for uid in (1, 2):
        client.post("/api/app/register", headers=H(uid), json={"name": f"U{uid}", "region": "bukhara", "lang": "en"})
    fid = client.post("/api/app/fields", headers=H(1), json={"name": "Mine", "region": "bukhara"}).json()["id"]
    assert client.get(f"/api/app/fields/{fid}/status", headers=H(2)).status_code == 404
    assert client.get(f"/api/app/fields/{fid}/plan", headers=H(2)).status_code == 404
    assert client.put(f"/api/app/fields/{fid}", headers=H(2), json={"crop": "rice"}).status_code == 404
    assert client.delete(f"/api/app/fields/{fid}", headers=H(2)).status_code == 404
    assert db.field_get(fid)["crop"] == "cotton"
    assert [f["id"] for f in client.get("/api/app/bootstrap", headers=H(2)).json()["fields"]] == []


def test_community(client):
    for uid in (1, 2):
        client.post("/api/app/register", headers=H(uid), json={"name": f"U{uid}", "region": "bukhara", "lang": "en"})
    assert client.post("/api/app/posts", headers=H(1), json={"text": "short"}).status_code == 422
    assert client.post("/api/app/posts", headers=H(1), json={"text": "<script>alert(1)</script> flush in winter"}).status_code == 200
    posts = client.get("/api/app/posts?scope=all", headers=H(2)).json()
    assert len(posts) == 1 and posts[0]["mine"] is False
    pid = posts[0]["id"]
    assert client.post(f"/api/app/posts/{pid}/like", headers=H(2)).json()["likes"] == 1
    assert client.post(f"/api/app/posts/{pid}/report", headers=H(2)).json()["new"] is True
    assert client.post(f"/api/app/posts/{pid}/report", headers=H(2)).json()["new"] is False
    assert client.delete(f"/api/app/posts/{pid}", headers=H(2)).status_code == 403
    assert client.delete(f"/api/app/posts/{pid}", headers=H(1)).status_code == 200
    for _ in range(5):
        client.post("/api/app/posts", headers=H(1), json={"text": "another useful tip here"})
    assert client.post("/api/app/posts", headers=H(1), json={"text": "one too many today"}).status_code == 429


def test_settings_and_delete_account(client):
    client.post("/api/app/register", headers=H(), json={"name": "Ali", "region": "navoi", "lang": "uz"})
    client.post("/api/app/settings", headers=H(), json={"lang": "en", "notify": False, "region": "fergana"})
    u = client.get("/api/app/bootstrap", headers=H()).json()["user"]
    assert (u["lang"], u["notify"], u["region"]) == ("en", False, "fergana")
    assert client.post("/api/app/settings", headers=H(), json={"lang": "xx"}).status_code == 422
    client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "navoi"})
    assert client.delete("/api/app/account", headers=H()).status_code == 200
    assert db.user_get(1) is None and db.fields_of(1) == []


def test_mini_app_page_served(client):
    r = client.get("/app")
    assert r.status_code == 200 and "telegram-web-app.js" in r.text and r.headers["cache-control"] == "no-store"


# ---------- new Mini App endpoints (district view, crops, map, field log, priorities) ----------
def reg(client, uid=1, region="nukus"):
    client.post("/api/app/register", headers=H(uid), json={"name": f"U{uid}", "region": region, "lang": "en"})


def test_district_view_status_crops_plan(client):
    reg(client)
    s = client.get("/api/app/area/bukhara/status", headers=H()).json()
    assert s["target"]["type"] == "area" and s["advice"]["irrigation"]["status"] in ("IRRIGATE", "MONITOR", "WAIT")
    assert s["regional"]["region"] == "Bukhara" and s["regional"]["pct"] == 75.1          # published regional statistic
    c = s["climate"]
    assert c["data_date"] and len(c["chart"]) > 30 and c["latest"]["temp"] is not None and "rain_7d" in c
    assert client.get("/api/app/area/atlantis/status", headers=H()).status_code == 404
    assert client.get("/api/app/area/bukhara/status?crop=bananas", headers=H()).status_code == 422
    cr = client.get("/api/app/area/gulistan/crops", headers=H()).json()
    assert cr["ec_known"] is False and cr["crops"][0]["fit"] == "good" and all("name" in x for x in cr["crops"]) and len(cr["rotation"]) == 3
    assert client.get("/api/app/area/nukus/plan", headers=H()).json()["outlook"]


def test_login_required_for_district_view(client):
    assert client.get("/api/app/area/nukus/status").status_code == 401
    assert client.get("/api/app/map").status_code == 401


def test_farmer_priorities_change_crops_and_rotation(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus", "groundwater": "shallow"}).json()["id"]
    base = client.get(f"/api/app/fields/{fid}/crops", headers=H()).json()
    assert all(c["notes"] == [] for c in base["crops"])
    r = client.put(f"/api/app/fields/{fid}", headers=H(), json={"water": "scarce", "pref_crops": ["barley", "wheat"]})
    assert r.status_code == 200 and r.json()["water"] == "scarce" and r.json()["prefs"] == ["barley", "wheat"]
    d = client.get(f"/api/app/fields/{fid}/crops", headers=H()).json()
    thirsty = [c for c in d["crops"] if c["water_demand"] == "high"]
    assert thirsty and all(c["notes"] == ["water_scarce"] for c in thirsty)
    assert [c["crop"] for c in d["crops"] if c["preferred"]] == [c["crop"] for c in d["crops"] if c["crop"] in ("barley", "wheat")]
    from app.engine.crops import WATER_DEMAND
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"water": "lots"}).status_code == 422
    assert client.put(f"/api/app/fields/{fid}", headers=H(), json={"pref_crops": ["bananas"]}).status_code == 422
    assert WATER_DEMAND["rice"] == "high"


def test_field_log_events_update_field(client):
    reg(client)
    fid = client.post("/api/app/fields", headers=H(), json={"name": "F", "region": "nukus", "last_flush": "gt12"}).json()["id"]
    assert client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["flush_days"] == 500
    r = client.post(f"/api/app/fields/{fid}/events", headers=H(), json={"kind": "flushed"}).json()
    assert r["field"]["flush_days"] == 0 and r["events"][0]["kind"] == "flushed"
    assert client.get(f"/api/app/fields/{fid}/status", headers=H()).json()["flush_days"] == 0
    assert client.post(f"/api/app/fields/{fid}/events", headers=H(), json={"kind": "sown"}).json()["field"]["stage"] == "initial"
    assert client.post(f"/api/app/fields/{fid}/events", headers=H(), json={"kind": "harvested"}).json()["field"]["stage"] == "fallow"
    assert client.post(f"/api/app/fields/{fid}/events", headers=H(), json={"kind": "dance"}).status_code == 422
    reg(client, 2)
    assert client.post(f"/api/app/fields/{fid}/events", headers=H(2), json={"kind": "irrigated"}).status_code == 404   # not your field


def test_map_has_pilots_and_own_fields(client):
    reg(client)
    client.post("/api/app/fields", headers=H(), json={"name": "Mine", "region": "fergana"})
    pts = client.get("/api/app/map", headers=H()).json()
    assert [p["id"] for p in pts if p["kind"] == "area"] == ["nukus", "gulistan", "bukhara"]
    assert any(p["kind"] == "field" and p["name"] == "Mine" for p in pts)
    assert all(p["status"] in ("IRRIGATE", "MONITOR", "WAIT") and p["level"] in ("LOW", "MEDIUM", "HIGH") for p in pts)


def test_bootstrap_serves_all_text_and_thresholds(client):
    b = client.get("/api/app/bootstrap", headers=H()).json()
    assert b["meta"]["pilots"] == ["nukus", "gulistan", "bukhara"] and b["meta"]["thresholds"] == {"dry": 0.3, "watch": 0.45}
    for k in ("h_salt", "st_IRRIGATE", "a_question", "because", "plan_head", "months"):
        assert set(b["i18n"][k]) >= {"en", "uz", "ru"}, k


def test_old_database_is_migrated(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.executescript("CREATE TABLE fields (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT, lat REAL, lon REAL, "
                    "region TEXT, crop TEXT DEFAULT 'cotton', stage TEXT DEFAULT 'mid', groundwater TEXT DEFAULT 'unknown', "
                    "drainage TEXT DEFAULT 'unknown', last_flush_days INTEGER, ec_class TEXT, notify INTEGER DEFAULT 1, last_sent TEXT);"
                    "INSERT INTO fields (user_id, name, lat, lon) VALUES (1, 'Old', 41.5, 60.6);")
    c.commit(); c.close()
    monkeypatch.setattr(config, "DB_PATH", str(path))
    db.init()
    f = db.fields_of(1)[0]
    assert f["name"] == "Old" and f["water"] == "normal" and f["flush_date"] is None
