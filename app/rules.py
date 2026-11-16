"""Loads app/rules.json: the single table of thresholds the engine uses (editable, versioned, labelled)."""
import json
import pathlib

_PATH = pathlib.Path(__file__).parent / "rules.json"
DATA = json.loads(_PATH.read_text(encoding="utf-8"))
RULES = DATA["rules"]


def val(key: str):
    return RULES[key]["value"]


def table(lang: str = "en") -> dict:
    """Public view of the rules for the app's 'Rules & thresholds' screen."""
    return {"version": DATA["version"], "validated_by": DATA["validated_by"], "note": DATA["note"],
            "rules": [{"id": k, "group": r["group"], "value": r["value"], "unit": r["unit"], "source": r["source"],
                       "label": r["label"].get(lang, r["label"]["en"]), "validated": not r["source"].startswith("placeholder")}
                      for k, r in RULES.items()]}
