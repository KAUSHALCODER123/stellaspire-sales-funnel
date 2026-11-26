"""Account fit and lead priority, ported from web_agents.py."""
from .config import settings
from .roles import FAMILIES, buyer_rank

_HARD_DQ = {"staffing_agency", "investor", "media", "government", "education", "non_profit"}
_SOFT_DQ = {"recent_layoffs", "hiring_freeze"}


def score_fit(brief: dict, family: str) -> dict:
    """Account-tiering ICP fit, 0-10: industry 3, size 3, buyer persona 2, no disqualifier 2."""
    lo, hi = FAMILIES[family].headcount
    n = int(brief.get("employee_estimate") or 0)
    size = 1 if n <= 0 else 3 if lo <= n <= hi else 1 if lo * 0.5 <= n <= hi * 1.5 else 0
    industry = {"exact": 3, "adjacent": 1}.get(brief.get("industry_match"), 0)
    persona = 2 if any(buyer_rank(t, family) is not None for t in brief.get("buyer_titles_found") or []) else 1
    dq = brief.get("disqualifier") or "none"
    clean = 0 if dq in _HARD_DQ else 1 if dq in _SOFT_DQ else 2
    return {"industry": industry, "size": size, "size_verified": n > 0, "persona": persona, "clean": clean,
            "total": industry + size + persona + clean}


def priority(fit: dict, brief: dict, roles: int, signals: int, allowed: list[str]) -> str:
    """Lead-triage tiers. A verified open role is already a timing trigger; a dated growth signal or
    several open roles in the segment make it a hot one."""
    in_country = brief.get("india_presence") or str(brief.get("hq_country", "")).strip().lower() in allowed
    if fit["clean"] == 0 or not in_country:
        return "DQ"
    if fit["total"] >= 8 and (signals or roles >= 3):
        return "P0"
    return "P1" if fit["total"] >= 6 else "P2"


def fit(inp: dict) -> dict:
    if inp["family"] not in FAMILIES:
        raise ValueError(f"unknown family: {inp['family']}")
    scored = score_fit(inp["brief"], inp["family"])
    allowed = [c.lower() for c in settings().get("allowed_countries", ["india"])]
    return {"fit": scored, "priority": priority(scored, inp["brief"], int(inp["roles"]), int(inp["signals"]), allowed)}
