"""Which labels a sent thread is missing.

Gmail will not let the connector label a draft, so drafts carry no labels. Once Nikita sends one, the run labels the
thread: the step from how many of our messages it holds, and the campaign from the ledger note written when the draft
was made (or from the imported leads file for leads carried over from the old funnel).
"""
import json
import re

from .campaigns import load_campaigns
from .config import config_dir

STEPS = 5
STEP_LABEL = re.compile(r"^SS/Step-([1-5])$")


def _imported_slug() -> str | None:
    return next((c["slug"] for c in load_campaigns() if c.get("source") == "imported"), None)


def _imported_emails() -> set[str]:
    path = config_dir() / "imported-leads.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {lead["contact"]["email"].lower() for lead in data.get("leads", [])}


def sync_plan(inp: dict) -> dict:
    ledger = {e["email"].strip().lower(): e["campaign"] for e in inp.get("ledger") or []}
    imported, slug = _imported_emails(), _imported_slug()
    actions, unmatched = [], []
    for t in inp["threads"]:
        labels = set(t.get("labels") or [])
        step = min(max(int(t["our_messages"]), 1), STEPS)
        have = max((int(m.group(1)) for l in labels if (m := STEP_LABEL.match(l))), default=0)
        add = [f"SS/Step-{step}"] if have < step else []
        if not any(l.startswith("SS/C-") for l in labels):
            email = t["to"].strip().lower()
            campaign = ledger.get(email) or (slug if email in imported else None)
            if campaign:
                add.append(f"SS/C-{campaign}")
            else:
                unmatched.append(t["thread_id"])
        if add:
            actions.append({"thread_id": t["thread_id"], "add": add})
    return {"actions": actions, "unmatched": unmatched}
