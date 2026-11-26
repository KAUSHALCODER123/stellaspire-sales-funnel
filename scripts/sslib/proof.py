"""Placement proof sentence and the facts the model is allowed to use (drafting.py _placement_proof / build_facts)."""
import re
from datetime import timedelta

from .calendar_ist import IST, now_ist, parse_dt
from .config import settings
from .roles import FAMILIES, classify_title

RECENT_HIRE_DAYS = 90
LONG_OPEN_DAYS = 45  # from here a role's age is stated: open this long, it is hard to fill
OFFER_SIZE = 3  # profiles offered in the closing question; the only digit the model may write


def _role_key(title: str) -> str:
    words = re.sub(r"[^a-z0-9+#]+", " ", title.casefold()).split()
    levels = {"sr", "jr", "senior", "junior", "lead", "principal", "staff", "i", "ii", "iii", "iv"}
    return " ".join(word for word in words if word not in levels)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _date(value):
    dt = parse_dt(value)
    return None if dt is None else dt.astimezone(IST).date()


def proof(inp: dict) -> dict:
    """Evidence sentence from Hired applications, or none.

    Matches the role's title first; failing that, uses the whole role family under its own label. Each Hired
    application counts once. updated_at is only the application's update date, so the recent figure counts
    updates in the window; missing or future dates are never recent. Offers are not counted.
    """
    role, family = inp["role"], inp["family"]
    rows = [r for r in inp["hired"] if classify_title(r["title"]) == family]
    key = _role_key(role)
    matched = [r for r in rows if key and _role_key(r["title"]) == key]
    if matched:
        scope, label = "role", role
    elif family in FAMILIES and rows:
        matched, scope, label = rows, "family", FAMILIES[family].label
    else:
        return {"proof": None, "basis": {}}
    today = now_ist(inp.get("now")).date()
    dates = [_date(r.get("updated_at")) for r in matched]
    recent = sum(d is not None and today - timedelta(days=RECENT_HIRE_DAYS) <= d <= today for d in dates)
    # "Recently" means a Hired record updated inside the window (Hiresome has no hire date); with none,
    # the all-time count is stated without a time word rather than claiming recency it cannot show.
    count = recent or len(matched)
    sentence = f"We {'recently filled' if recent else 'have filled'} {_plural(count, f'{label} role')}."
    basis = {"scope": scope, "hired_applications": len(matched), "postings": len({r["job_id"] for r in matched}),
             "recently_updated": recent, "recent_window_days": RECENT_HIRE_DAYS,
             "undated": sum(d is None for d in dates), "future_dated": sum(d is not None and d > today for d in dates)}
    return {"proof": sentence, "basis": basis}


def facts(inp: dict) -> dict:
    """Facts for one contact and one verified open role. A role open LONG_OPEN_DAYS or longer carries its exact age."""
    cfg, role = settings(), inp["role"]
    contact, company = inp["contact"], inp["company"]
    family, today, posted = classify_title(role), now_ist(inp.get("now")).date(), _date(inp.get("posted_at"))
    open_days = (today - posted).days if posted and posted <= today else None
    out = {
        "recipient_first_name": contact["full_name"].split()[0],
        "recipient_title": contact.get("title"),
        "company": company["name"],
        "company_industry": company.get("industry"),
        "company_city": company.get("city"),
        "their_open_roles": [role],
        "role_listed_on": f"{company['name']}'s careers page" if inp.get("on_employer_board") else None,
        **({"role_posted_on": f"{posted:%B} {posted.day}", "role_open_days": open_days}
           if open_days is not None and open_days >= LONG_OPEN_DAYS else {}),
        "our_focus": FAMILIES[family].label if family in FAMILIES else None,
        "sender_name": cfg["sender_name"],
        "sender_company": cfg["sender_company"],
        "placement_proof": inp.get("proof"),
    }
    return {**{k: v for k, v in out.items() if v not in (None, [], "")}, "offer_size": OFFER_SIZE}
