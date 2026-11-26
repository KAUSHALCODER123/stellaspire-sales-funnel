"""Chat-managed setting overrides: a small allowed set, bounds-checked. Everything else stays in the plugin file."""
import json
import re

from .config import base_settings, override_path

SEND_MODES = ("dry_run", "draft", "send")
WHEN_NO_CAMPAIGN = ("wait", "default")
EMAIL = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[A-Za-z]{2,}$")
DOMAIN = re.compile(r"^(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$")


def _int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _str_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def _bounded(lo, hi):
    return lambda v: _int(v) and lo <= v <= hi


# key -> (check, message)
RULES = {
    "paused": (lambda v: isinstance(v, bool), "paused must be true or false"),
    "send_mode": (lambda v: v in SEND_MODES and isinstance(v, str), f"send_mode must be one of {list(SEND_MODES)}"),
    "linkedin_doc_url": (lambda v: isinstance(v, str) and (v == "" or (v.startswith("https://") and " " not in v and len(v) > 8)),
                         "linkedin_doc_url must be an https URL or an empty string"),
    "mailbox_daily_cap": (_bounded(1, 25), "mailbox_daily_cap must be a whole number from 1 to 25"),
    "target_cities": (_str_list, "target_cities must be a list of city names"),
    "exclude_domains": (lambda v: _str_list(v) and all(DOMAIN.match(x.strip().lower()) for x in v),
                        "exclude_domains must be a list of domains like example.com"),
    "when_no_campaign": (lambda v: v in WHEN_NO_CAMPAIGN and isinstance(v, str),
                         f"when_no_campaign must be one of {list(WHEN_NO_CAMPAIGN)}"),
    "alert_email": (lambda v: isinstance(v, str) and bool(EMAIL.match(v)), "alert_email must be a valid email address"),
    "max_companies_researched_per_run": (_bounded(1, 40), "max_companies_researched_per_run must be a whole number from 1 to 40"),
}


def check_overrides(overrides) -> list[str]:
    if not isinstance(overrides, dict):
        return ["overrides must be an object"]
    problems = []
    for key, value in overrides.items():
        if key not in RULES:
            problems.append(f"{key} cannot be changed in chat (allowed: {', '.join(RULES)})")
        elif not RULES[key][0](value):
            problems.append(RULES[key][1])
    return problems


def effective(overrides: dict) -> dict:
    return {**base_settings(), **overrides}


def settings_check(inp: dict) -> dict:
    overrides = inp.get("overrides", {})
    problems = check_overrides(overrides)
    return {"ok": not problems, "problems": problems, "effective": effective(overrides if not problems else {})}


def load_settings(inp: dict) -> dict:
    overrides = inp.get("overrides", {})
    problems = check_overrides(overrides)
    if problems:
        raise ValueError("invalid settings overrides: " + "; ".join(problems))
    path = override_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides), encoding="utf-8")
    return {"ok": True, "problems": [], "effective": effective(overrides)}
