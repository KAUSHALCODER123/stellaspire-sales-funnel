"""Leads carried over from the old funnel (config/imported-leads.json): which of them may be written to today.

The role freshness rule is the same as for new leads (role_check): 30 days when the employer's own board lists the role,
14 days when only Apollo does. Contact and history rules stay in check-contacts, which the daily run calls next.
"""
import json

from .config import config_dir
from .roles import role_check


def _load() -> dict:
    path = config_dir() / "imported-leads.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"leads": []}


def imported_leads(inp: dict) -> dict:
    limit = int(inp.get("limit", 10))
    leads = _load().get("leads", [])
    fresh, skipped = [], []
    for lead in leads:
        role, contact = lead["role"], lead["contact"]
        check = role_check({"title": role["title"], "posted_at": role.get("posted_at"), "status": "active",
                            "on_employer_board": bool(role.get("on_employer_board")), "now": inp.get("now")})
        if check["fresh"]:
            fresh.append({**lead, "age_days": check["age_days"]})
        else:
            skipped.append({"email": contact["email"], "reason": check["reason"]})
    # Roles the employer's own board lists come first, then the newest postings.
    fresh.sort(key=lambda lead: (not lead["role"].get("on_employer_board"), lead["age_days"]))
    return {"candidates": fresh[:max(limit, 0)], "skipped": skipped, "fresh_total": len(fresh), "total": len(leads)}
