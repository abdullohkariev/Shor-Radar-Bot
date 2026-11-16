"""Every text key the Mini App page uses must exist in en, uz and ru (no raw key names on screen)."""
import pathlib
import re

from app.appstrings import APP
from app.messages import T as MSG
from app.ui import UI

HTML = (pathlib.Path(__file__).resolve().parent.parent / "app" / "static" / "app.html").read_text(encoding="utf-8")
ALL = {**MSG, **UI, **APP}
DYNAMIC = {  # keys built at runtime in app.html: prefix -> suffixes
    "a_ev_": ["irrigated", "flushed", "sown", "harvested"], "a_wa_": ["normal", "limited", "scarce"],
    "a_note_": ["water_limited", "water_scarce"], "st_": ["IRRIGATE", "MONITOR", "WAIT"], "a_tol_": ["tolerant", "moderate", "sensitive"],
}


def used_keys():
    static = set(re.findall(r'\bT\("([A-Za-z0-9_]+)"', HTML))
    for pre, sufs in DYNAMIC.items():
        static |= {pre + s for s in sufs}
    # keys passed through arrays/objects like fitL = { good: "a_fit_good", ... } or [["region", "c_region"], ...]
    static |= set(re.findall(r'"((?:a|c|h|st|lv)_[A-Za-z0-9_]+)"', HTML))
    return {k for k in static if not k.endswith("_")}


def test_all_used_keys_exist_in_three_languages():
    missing = []
    for k in sorted(used_keys()):
        e = ALL.get(k)
        if e is None:
            missing.append((k, "no entry"))
            continue
        for lang in ("en", "uz", "ru"):
            if not e.get(lang):
                missing.append((k, lang))
    assert not missing, missing


def test_every_app_string_has_three_languages():
    for k, e in APP.items():
        assert set(e) >= {"en", "uz", "ru"}, k
        assert all(e[l].strip() for l in ("en", "uz", "ru")), k


def test_format_placeholders_match_across_languages():
    for k, e in APP.items():
        ph = {l: set(re.findall(r"\{(\w+)\}", e[l])) for l in ("en", "uz", "ru")}
        assert ph["en"] == ph["uz"] == ph["ru"], (k, ph)


def test_short_alert_leads_with_action_in_every_language():
    from app import bot as botmod
    from app.engine.advisor import build_advice
    from app.data.demo import demo_forecast, demo_power
    a = build_advice(demo_power(41.0, 64.5), demo_forecast(41.0, 64.5), 41.0, 64.5)
    for lang in ("en", "uz", "ru"):
        text = botmod.short_alert(a, lang)
        first = text.splitlines()[0]
        assert APP[botmod.DO_KEY[a["irrigation"]["status"]]][lang] in first       # action comes first
        assert "{" not in text and "a_" not in first                              # no unfilled placeholders or raw keys
        assert len(text) < 700                                                    # short enough to read at a glance
