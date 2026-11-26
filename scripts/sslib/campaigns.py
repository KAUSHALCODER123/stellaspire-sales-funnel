"""Campaigns: targeted batches of outreach with a contact target. Config is a read-only seed list; campaign notes and counts come from Gmail.

Targeting is by company and role traits only (families, cities, industries, headcount, buyer titles).
A person starts a campaign (status "active") and ends it (target, end date, "paused" or "done"); the plugin never does.
"""
import json
import re
from datetime import date

from .calendar_ist import now_ist
from .config import config_dir, settings
from .roles import FAMILIES

STATUSES = ("draft", "active", "paused", "done")
WHEN_NO_CAMPAIGN = ("wait", "default")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
COUNT_KEYS = ("contacted", "active_threads", "replied", "interested", "meeting", "won", "bounced")


def _config_campaigns() -> list[dict]:
    path = config_dir() / "campaigns.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("campaigns", [])


def _validate(c) -> None:
    if not isinstance(c, dict):
        raise ValueError("campaign entry must be an object")
    name = c.get("slug", "?")
    for key in ("slug", "name", "status", "start_date", "target_contacts"):
        if key not in c:
            raise KeyError(f"campaign {name} missing {key}")
    if not SLUG.match(str(c["slug"])):
        raise ValueError(f"campaign slug must be kebab-case: {c['slug']}")
    if c["status"] not in STATUSES:
        raise ValueError(f"campaign {c['slug']}: status must be one of {STATUSES}")
    t = c["target_contacts"]
    if not isinstance(t, int) or isinstance(t, bool) or t < 1:
        raise ValueError(f"campaign {c['slug']}: target_contacts must be a positive integer")


def load_campaigns(from_gmail: list | None = None) -> list[dict]:
    """Config seed list merged with the newest Gmail note per slug (a Gmail entry overrides config by slug)."""
    items = list(_config_campaigns())
    seen = set()
    for c in items:
        _validate(c)
        if c["slug"] in seen:
            raise ValueError(f"duplicate campaign slug: {c['slug']}")
        seen.add(c["slug"])
    if from_gmail is not None and not isinstance(from_gmail, list):
        raise ValueError("campaigns must be a list")
    for g in from_gmail or []:
        _validate(g)
        for i, c in enumerate(items):
            if c["slug"] == g["slug"]:
                items[i] = g
                break
        else:
            items.append(g)
    return items


def _int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def campaign_check(inp: dict) -> dict:
    c = inp.get("campaign")
    if not isinstance(c, dict):
        raise ValueError("campaign must be an object")
    existing = inp.get("existing_slugs") or []
    if not isinstance(existing, list):
        raise ValueError("existing_slugs must be a list")
    today_ = now_ist(inp.get("now")).date()
    n = dict(c)
    n.setdefault("priority", 1)
    n.setdefault("start_date", today_.isoformat())
    n.setdefault("status", "draft")
    problems = []
    slug = n.get("slug")
    if not n.get("name"):
        problems.append("name is required")
    if not isinstance(slug, str) or not SLUG.match(slug):
        problems.append("slug must be kebab-case, like pune-sales-hiring")
    elif slug in existing and not inp.get("update"):
        problems.append(f"slug {slug} is already used; pick another, or confirm this is a change to that campaign")
    if n["status"] not in STATUSES:
        problems.append(f"status must be one of {list(STATUSES)}")
    fam = n.get("families")
    valid = ", ".join(f"{k} ({v.label})" for k, v in FAMILIES.items())
    if not isinstance(fam, list) or not fam or not all(isinstance(f, str) for f in fam):
        problems.append(f"families must be a non-empty list of keys. Valid keys: {valid}")
    else:
        bad = [f for f in fam if f not in FAMILIES]
        if bad:
            problems.append(f"unknown families {bad}. Valid keys: {valid}")
    hc = n.get("headcount")
    if not isinstance(hc, list) or len(hc) != 2 or not all(_int(x) for x in hc) or hc[0] < 0 or hc[0] >= hc[1]:
        problems.append("headcount must be [min, max] with min below max")
    t = n.get("target_contacts")
    if not _int(t) or not 1 <= t <= 2000:
        problems.append("target_contacts must be a whole number from 1 to 2000")
    start = end = None
    try:
        start = date.fromisoformat(str(n["start_date"]))
    except ValueError:
        problems.append("start_date must be YYYY-MM-DD")
    if n.get("end_date"):
        try:
            end = date.fromisoformat(str(n["end_date"]))
        except ValueError:
            problems.append("end_date must be YYYY-MM-DD")
    if start and end and end <= start:
        problems.append("end_date must be after start_date")
    return {"ok": not problems, "problems": problems, "normalized": n}


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def _counts(raw: dict | None) -> dict:
    raw = raw or {}
    return {k: int(raw.get(k, 0) or 0) for k in COUNT_KEYS}


def campaign(inp: dict) -> dict:
    counts, new_cap = inp.get("counts") or {}, int(inp["new_cap"])
    if not isinstance(counts, dict):
        raise ValueError("counts must be an object")
    mode = settings().get("when_no_campaign", "wait")
    if mode not in WHEN_NO_CAMPAIGN:
        raise ValueError(f"when_no_campaign must be one of {WHEN_NO_CAMPAIGN}")
    day = now_ist(inp.get("now")).date()
    active, completed = [], []
    for c in load_campaigns(inp.get("campaigns")):
        if c["status"] != "active" or date.fromisoformat(c["start_date"]) > day:
            continue
        n = _counts(counts.get(c["slug"]))
        end = c.get("end_date")
        if n["contacted"] >= c["target_contacts"]:
            reason = "target_reached"
        elif end and date.fromisoformat(end) < day:
            reason = "end_date_passed"
        else:
            active.append(c)
            continue
        results = {**n, "reply_rate": _rate(n["replied"], n["contacted"]),
                   "interested_rate": _rate(n["interested"], n["contacted"])}
        completed.append({"slug": c["slug"], "name": c["name"], "reason": reason, "results": results,
                          "all_sequences_finished": n["active_threads"] == 0})
    left, out = max(new_cap, 0), []
    for c in sorted(active, key=lambda c: -int(c.get("priority", 0))):  # stable: config order breaks ties
        remaining = c["target_contacts"] - _counts(counts.get(c["slug"]))["contacted"]
        quota = min(remaining, left)
        left -= quota
        out.append({"slug": c["slug"], "name": c["name"], "families": c.get("families", []),
                    "cities": c.get("cities", []), "industries": c.get("industries", []),
                    "headcount": c.get("headcount"), "seniority": c.get("seniority", []),
                    "angle": c.get("angle"), "remaining": remaining, "quota_today": quota})
    none_active = not out
    return {"active": out, "completed": completed,
            "default_targeting": none_active and mode == "default",
            "waiting_for_campaign": none_active and mode == "wait"}
