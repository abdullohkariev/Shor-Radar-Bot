"""Storage: accounts, fields, daily advice log, community posts, AI-usage counters. One local SQLite file (config.DB_PATH)."""
import contextlib
import datetime as dt
import sqlite3

from . import config

FIELD_COLS = {"name", "lat", "lon", "region", "crop", "stage", "groundwater", "drainage",
              "last_flush_days", "ec_class", "notify", "last_sent", "water", "pref_crops", "flush_date",
              "ece", "ece_date", "water_ec"}
USER_COLS = {"lang", "name", "region", "notify", "registered", "alert_hour", "role"}


@contextlib.contextmanager
def _sqlite_conn():
    """`with _conn() as c:` commits on success, rolls back on error, and ALWAYS closes the connection
    (sqlite3's own context manager only commits, so connections used to pile up until garbage collection)."""
    c = sqlite3.connect(config.DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA foreign_keys=ON")
        with c:
            yield c
    finally:
        c.close()


_conn = _sqlite_conn


def _insert_id(c, sql: str, params) -> int:
    """INSERT and return the new row id."""
    return c.execute(sql, params).lastrowid


# ---------------------------------------------------------------- schema
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz', name TEXT, region TEXT,
    notify INTEGER DEFAULT 1, registered INTEGER DEFAULT 0, created TEXT);
CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT, lat REAL, lon REAL,
    region TEXT, crop TEXT DEFAULT 'cotton', stage TEXT DEFAULT 'mid', groundwater TEXT DEFAULT 'unknown',
    drainage TEXT DEFAULT 'unknown', last_flush_days INTEGER, ec_class TEXT,
    notify INTEGER DEFAULT 1, last_sent TEXT);
CREATE INDEX IF NOT EXISTS ix_fields_user ON fields(user_id);
CREATE TABLE IF NOT EXISTS advice_log (
    field_id INTEGER, day TEXT, irrigation TEXT, flush TEXT, salt_level TEXT, salt_score INTEGER,
    PRIMARY KEY (field_id, day));
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, author TEXT, region TEXT,
    text TEXT NOT NULL, created TEXT NOT NULL, hidden INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS post_likes (post_id INTEGER, user_id INTEGER, PRIMARY KEY (post_id, user_id));
CREATE TABLE IF NOT EXISTS post_reports (post_id INTEGER, user_id INTEGER, PRIMARY KEY (post_id, user_id));
CREATE TABLE IF NOT EXISTS field_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, field_id INTEGER NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assistant_usage (user_id INTEGER, day TEXT, n INTEGER DEFAULT 0, PRIMARY KEY (user_id, day));
"""


def init():
    with _sqlite_conn() as c:
        c.execute("PRAGMA journal_mode=WAL")      # web requests and the bot share this file: let readers and a writer work together
        c.executescript(_SQLITE_SCHEMA)
        # light migrations for databases created by earlier versions
        for table, col in (("fields", "water TEXT DEFAULT 'normal'"), ("fields", "pref_crops TEXT DEFAULT ''"), ("fields", "flush_date TEXT"),
                           ("fields", "ece REAL"), ("fields", "ece_date TEXT"), ("fields", "water_ec REAL"),
                           ("users", "alert_hour INTEGER DEFAULT 7"), ("users", "role TEXT DEFAULT 'farmer'")):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass


def reset_all_for_tests():
    """Empty every table (tests only)."""
    with _conn() as c:
        for t in ("users", "fields", "advice_log", "posts", "post_likes", "post_reports", "field_events", "assistant_usage"):
            c.execute(f"DELETE FROM {t}")


# ---------- AI assistant usage (counts only, never the questions) ----------
def assistant_used_today(uid: int) -> int:
    with _conn() as c:
        r = c.execute("SELECT n FROM assistant_usage WHERE user_id=? AND day=?", (uid, dt.date.today().isoformat())).fetchone()
        return r[0] if r else 0


def assistant_total_today() -> int:
    with _conn() as c:
        return c.execute("SELECT COALESCE(SUM(n), 0) FROM assistant_usage WHERE day=?", (dt.date.today().isoformat(),)).fetchone()[0]


def assistant_record(uid: int):
    with _conn() as c:
        c.execute("INSERT INTO assistant_usage (user_id, day, n) VALUES (?,?,1) ON CONFLICT (user_id, day) DO UPDATE SET n = assistant_usage.n + 1",
                  (uid, dt.date.today().isoformat()))


# ---------- users ----------
def user_get(uid: int):
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return dict(r) if r else None


def user_upsert(uid: int, **kw):
    kw = {k: v for k, v in kw.items() if k in USER_COLS}
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO users (user_id, created) VALUES (?, ?)", (uid, dt.datetime.now().isoformat()))
        if kw:
            c.execute(f"UPDATE users SET {', '.join(k + '=?' for k in kw)} WHERE user_id=?", (*kw.values(), uid))


def user_delete(uid: int):
    """Delete the account and everything tied to it (fields, logs, posts, likes)."""
    with _conn() as c:
        fids = [r[0] for r in c.execute("SELECT id FROM fields WHERE user_id=?", (uid,)).fetchall()]
        pids = [r[0] for r in c.execute("SELECT id FROM posts WHERE user_id=?", (uid,)).fetchall()]
        for f in fids:
            c.execute("DELETE FROM advice_log WHERE field_id=?", (f,))
            c.execute("DELETE FROM field_events WHERE field_id=?", (f,))
        for p in pids:
            c.execute("DELETE FROM post_likes WHERE post_id=?", (p,))
            c.execute("DELETE FROM post_reports WHERE post_id=?", (p,))
        c.execute("DELETE FROM posts WHERE user_id=?", (uid,))
        c.execute("DELETE FROM post_likes WHERE user_id=?", (uid,))
        c.execute("DELETE FROM post_reports WHERE user_id=?", (uid,))
        c.execute("DELETE FROM fields WHERE user_id=?", (uid,))
        c.execute("DELETE FROM assistant_usage WHERE user_id=?", (uid,))
        c.execute("DELETE FROM users WHERE user_id=?", (uid,))


# ---------- fields ----------
def field_add(uid: int, name: str, region: str | None = None) -> int:
    with _conn() as c:
        return _insert_id(c, "INSERT INTO fields (user_id, name, region) VALUES (?, ?, ?)", (uid, name, region))


def field_update(fid: int, **kw):
    kw = {k: v for k, v in kw.items() if k in FIELD_COLS}
    if kw:
        with _conn() as c:
            c.execute(f"UPDATE fields SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), fid))


def field_get(fid: int):
    with _conn() as c:
        r = c.execute("SELECT * FROM fields WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None


def fields_of(uid: int):
    """Only fields that already have a location (half-finished ones are hidden)."""
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM fields WHERE user_id=? AND lat IS NOT NULL ORDER BY id", (uid,)).fetchall()]


def field_delete(fid: int):
    with _conn() as c:
        c.execute("DELETE FROM advice_log WHERE field_id=?", (fid,))
        c.execute("DELETE FROM field_events WHERE field_id=?", (fid,))
        c.execute("DELETE FROM fields WHERE id=?", (fid,))


def fields_for_alerts():
    with _conn() as c:
        return [dict(r) for r in c.execute(
            """SELECT f.*, u.lang AS lang, COALESCE(u.alert_hour, 7) AS alert_hour FROM fields f JOIN users u ON u.user_id = f.user_id
               WHERE f.lat IS NOT NULL AND f.notify=1 AND u.notify=1 AND u.registered=1""").fetchall()]


def flush_days(f: dict, today: dt.date | None = None):
    """Days since the last flush: from the farmer's logged date if there is one, else the value they entered."""
    if f.get("flush_date"):
        return max(0, ((today or dt.date.today()) - dt.date.fromisoformat(f["flush_date"])).days)
    return f.get("last_flush_days")


def event_add(fid: int, kind: str, day: dt.date | None = None):
    with _conn() as c:
        c.execute("INSERT INTO field_events (field_id, day, kind) VALUES (?,?,?)", (fid, (day or dt.date.today()).isoformat(), kind))


def last_event_days(fid: int, kind: str, today: dt.date | None = None):
    """Days since the latest logged event of this kind (0 = today), or None if never logged."""
    with _conn() as c:
        r = c.execute("SELECT day FROM field_events WHERE field_id=? AND kind=? ORDER BY day DESC, id DESC LIMIT 1", (fid, kind)).fetchone()
    return None if not r else max(0, ((today or dt.date.today()) - dt.date.fromisoformat(r[0])).days)


def events_of(fid: int, limit: int = 8):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT day, kind FROM field_events WHERE field_id=? ORDER BY id DESC LIMIT ?", (fid, limit)).fetchall()]


# ---------- advice history ----------
def log_advice(fid: int, advice: dict, day: dt.date | None = None):
    day = (day or dt.date.today()).isoformat()
    vals = (fid, day, advice["irrigation"]["status"], advice["flush"]["status"], advice["salinity"]["level"], advice["salinity"]["score"])
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO advice_log VALUES (?,?,?,?,?,?)", vals)


def recent_log(fid: int, limit: int = 7):
    with _conn() as c:
        rows = c.execute("SELECT * FROM advice_log WHERE field_id=? ORDER BY day DESC LIMIT ?", (fid, limit)).fetchall()
        return [dict(r) for r in rows][::-1]


# ---------- community ----------
def post_add(uid: int, author: str, region: str | None, text: str) -> int:
    with _conn() as c:
        return _insert_id(c, "INSERT INTO posts (user_id, author, region, text, created) VALUES (?,?,?,?,?)",
                          (uid, author, region, text, dt.datetime.now().isoformat(timespec="minutes")))


def posts_today(uid: int) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM posts WHERE user_id=? AND created>=?",
                         (uid, dt.date.today().isoformat())).fetchone()[0]


def _with_likes(c, rows):
    out = []
    for r in rows:
        d = dict(r)
        d["likes"] = c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (d["id"],)).fetchone()[0]
        role = c.execute("SELECT role FROM users WHERE user_id=?", (d["user_id"],)).fetchone()
        d["role"] = (role[0] if role else None) or "farmer"
        out.append(d)
    return out


def posts_latest(region: str | None = None, limit: int = 5):
    with _conn() as c:
        if region:
            rows = c.execute("SELECT * FROM posts WHERE hidden=0 AND region=? ORDER BY id DESC LIMIT ?", (region, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM posts WHERE hidden=0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return _with_likes(c, rows)


def posts_of(uid: int, limit: int = 5):
    with _conn() as c:
        rows = c.execute("SELECT * FROM posts WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()
        return _with_likes(c, rows)


def post_get(pid: int):
    with _conn() as c:
        r = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def post_delete(pid: int):
    with _conn() as c:
        for t in ("post_likes", "post_reports"):
            c.execute(f"DELETE FROM {t} WHERE post_id=?", (pid,))
        c.execute("DELETE FROM posts WHERE id=?", (pid,))


def like_toggle(pid: int, uid: int) -> int:
    with _conn() as c:
        if c.execute("SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?", (pid, uid)).fetchone():
            c.execute("DELETE FROM post_likes WHERE post_id=? AND user_id=?", (pid, uid))
        else:
            c.execute("INSERT OR IGNORE INTO post_likes VALUES (?,?)", (pid, uid))
        return c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,)).fetchone()[0]


def report_post(pid: int, uid: int, hide_at: int = 3) -> bool:
    """Returns True if this report was new. Posts with >= hide_at reports are hidden."""
    with _conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO post_reports VALUES (?,?)", (pid, uid))
        if cur.rowcount == 0:
            return False
        n = c.execute("SELECT COUNT(*) FROM post_reports WHERE post_id=?", (pid,)).fetchone()[0]
        if n >= hide_at:
            c.execute("UPDATE posts SET hidden=1 WHERE id=?", (pid,))
        return True
