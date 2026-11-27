"""Role families Stellaspire recruits for, and how each maps to target companies and buyers.

Hiresome job titles are classified into a family by ordered regex rules (first match wins).
Ported verbatim from the engine's roles.py (the parts the plugin uses).
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .calendar_ist import IST, now_ist, parse_dt


@dataclass(frozen=True)
class Family:
    label: str
    pattern: str
    apollo_keywords: tuple[str, ...]
    buyer_titles: tuple[str, ...]  # priority order
    headcount: tuple[int, int] = (30, 1000)
    default_locations: tuple[str, ...] = ("Bengaluru, India",)


_HR_BUYERS = ("Head of Talent Acquisition", "Talent Acquisition Manager", "CHRO", "Head of HR", "HR Director")

# Order matters: more specific families first.
FAMILIES: dict[str, Family] = {
    "hardware_robotics": Family(
        "robotics, embedded and hardware engineering",
        r"firmware|embedded|hardware|motion|robot|machine vision|iot|hpc|network automation|plc|electronics",
        ("robotics", "embedded systems", "industrial automation", "iot", "semiconductors"),
        ("CTO", "VP Engineering", "Head of Engineering", "Founder") + _HR_BUYERS,
        (30, 1000), ("Bengaluru, India", "Hyderabad, India", "Pune, India")),
    "bfsi": Family(
        "BFSI and wealth management",
        r"private bank|banker|equity|wealth|relationship manager.*(debt|wealth)|debt|risk officer|credit|investment",
        ("wealth management", "private banking", "asset management", "investment banking", "nbfc"),
        ("CHRO", "Head of HR", "Head of Talent Acquisition", "Managing Director", "CEO"),
        (50, 5000), ("Mumbai, India", "New Delhi, India")),
    "real_estate": Family(
        "real estate sales and leadership",
        r"real estate|residential|realty|property|city head",
        ("real estate", "real estate developer", "residential projects"),
        ("Founder", "Managing Director", "CEO", "Head of HR", "HR Head"),
        (30, 3000), ("Pune, India", "Indore, India")),
    "healthcare": Family(
        "healthcare and biomedical",
        r"biomedical|clinical|medical|hospital|pharma|healthcare",
        ("medical devices", "healthcare", "hospital", "healthtech"),
        ("CEO", "Head of HR", "HR Head", "Head of Talent Acquisition"),
        (50, 3000), ("Hyderabad, India",)),
    "finance": Family(
        "finance and accounting",
        r"financ|fp&a|accountant|accounting|accounts|controller|\bcfo\b|tax|audit|chartered|compliance|company secretary",
        ("fintech", "saas", "venture backed", "d2c"),
        ("CFO", "Founder", "CEO", "Head of Finance") + _HR_BUYERS,
        (50, 1000), ("Bengaluru, India", "Mumbai, India", "Gurugram, India")),
    "hr": Family(
        "HR and talent",
        r"\bhr\b|human resource|talent|people ops|recruit|chro",
        ("information technology", "saas", "ecommerce"),
        ("CHRO", "Head of HR", "HR Director", "Founder", "CEO"),
        (100, 3000), ("Bengaluru, India", "Gurugram, India", "Kolkata, India")),
    "design": Family(
        "product design and UX",
        r"design|ui/ux|ux|visuali[sz]er|creative",
        ("saas", "consumer internet", "d2c"),
        ("Head of Design", "VP Product", "CPO", "Founder") + _HR_BUYERS,
        (30, 1000), ("Bengaluru, India", "Hyderabad, India", "Noida, India")),
    "tech_ai_data": Family(
        "software, AI and data engineering",
        r"engineer|developer|\bsde\b|machine learning|\bml\b|\bai\b|data|scientist|software|architect|"
        r"tech lead|full ?stack|backend|android|ios|devops|sailpoint|computer vision|copilot|product manager|"
        r"network platforms|artificial intelligence|research and development",
        ("artificial intelligence", "machine learning", "saas", "software development", "data analytics"),
        ("CTO", "VP Engineering", "Head of Engineering", "Co-Founder", "Founder") + _HR_BUYERS,
        (30, 500), ("Bengaluru, India", "Hyderabad, India", "Pune, India")),
    "growth": Family(
        "sales, marketing and e-commerce",
        r"sales|business development|marketing|brand|e-?commerce|partnership|tel+e ?caller|social media|\bseo\b|"
        r"insights|power trading|b2b",
        ("d2c", "consumer goods", "ecommerce", "retail", "consumer brand"),
        ("Founder", "CEO", "CMO", "Head of Sales", "Head of Marketing") + _HR_BUYERS,
        (30, 1000), ("Kolkata, India", "Mumbai, India", "Bengaluru, India")),
    "operations": Family(
        "operations, strategy and support",
        r"operation|\bops\b|logistic|support|strategy|strategic|ceo office|program|project|store|assistant|"
        r"excellence|quality|coordinator|executive",
        ("ecommerce", "logistics", "consumer services", "retail"),
        ("COO", "Head of Operations", "Founder", "CEO") + _HR_BUYERS,
        (50, 2000), ("Bengaluru, India", "Gurugram, India", "Kolkata, India")),
}

_COMPILED = [(key, re.compile(f.pattern, re.I)) for key, f in FAMILIES.items()]


_NOT_HIRED = re.compile(r"\b(intern|internship|interns|trainee|apprentice(ship)?)\b", re.I)


def is_hireable(title: str | None) -> bool:
    """False for roles Stellaspire does not recruit for (interns, trainees, apprentices)."""
    return not _NOT_HIRED.search(title or "")


def classify_title(title: str) -> str:
    for key, rx in _COMPILED:
        if rx.search(title or ""):
            return key
    return "other"


def _words(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9&]+', ' ', text.lower()).strip()} "


def buyer_rank(title: str | None, family: str) -> int | None:
    """Index of the first buyer title (priority order) the person's title contains, word-level; None if none."""
    if not title or family not in FAMILIES:
        return None
    t = _words(title)
    return next((i for i, b in enumerate(FAMILIES[family].buyer_titles) if _words(b) in t), None)


def title_matches_buyer(title: str | None, family: str) -> bool:
    return buyer_rank(title, family) is not None


MAX_POSTING_AGE = timedelta(days=30)
APOLLO_ONLY_MAX_AGE = timedelta(days=14)  # when only Apollo lists the role, not the employer's own board


def role_check(inp: dict) -> dict:
    """Is the role still open and recent enough to write about (hiring.py posting_is_recent rules)."""
    now, title = now_ist(inp.get("now")), inp["title"]
    raw = inp.get("posted_at")
    posted = parse_dt(raw)
    if posted is not None and len(raw) == 10:  # a bare date counts from the start of that IST day
        posted = datetime.combine(date.fromisoformat(raw), datetime.min.time(), IST)
    max_age = MAX_POSTING_AGE if inp["on_employer_board"] else APOLLO_ONLY_MAX_AGE
    if inp["status"] != "active":
        reason = "closed"
    elif not is_hireable(title):
        reason = "not_hireable"
    elif posted is None:
        reason = "undated"
    elif posted > now:
        reason = "future_dated"
    elif now - posted > max_age:
        reason = "stale"
    else:
        reason = None
    family = classify_title(title)
    return {"fresh": reason is None, "reason": reason,
            "age_days": None if posted is None else (now - posted).days,
            "family": None if family == "other" else family, "hireable": is_hireable(title)}
