"""Contact eligibility, ported from policy.py evaluate()/suppression_reasons() with inputs from JSON, not a DB."""
from datetime import timedelta

from .calendar_ist import now_ist, parse_dt
from .config import rows, settings
from .roles import title_matches_buyer

COOLDOWN = timedelta(days=90)
MAX_CONTACTS_PER_COMPANY = 2
ROLE_MAILBOXES = {"hr", "careers", "career", "jobs", "info", "contact", "hello", "admin", "support", "sales",
                  "recruitment", "hiring", "talent", "team", "office", "mail", "enquiry", "enquiries", "noreply",
                  "no-reply", "accounts", "billing", "marketing", "press", "media"}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().rstrip(".")


def _under(domain: str, base: str) -> bool:
    return bool(domain and base) and (domain == base or domain.endswith("." + base))


def _blocked(email: str, company_domain: str, entries: set[str]) -> bool:
    """An entry with @ blocks that address; any other entry blocks that domain and its subdomains."""
    domain = email.rpartition("@")[2]
    return email in entries or any("@" not in e and (_under(domain, e) or _under(company_domain, e)) for e in entries)


def check_contacts(inp: dict) -> dict:
    now, cfg = now_ist(inp.get("now")), settings()
    history = inp.get("history") or {}
    suppressed = {_norm(r.get("value")) for r in rows("do-not-contact.csv")} | {_norm(v) for v in inp.get("do_not_contact") or []}
    seeded = {_norm(v) for r in rows("already-contacted.csv") for v in (r.get("email"), r.get("domain"))} - {""}
    excluded = {_norm(d) for d in cfg.get("exclude_domains", []) if d.strip()}
    allowed_countries = {c.lower() for c in cfg.get("allowed_countries", ["india"])}
    sent = {}  # address -> latest send time
    for s in history.get("sent_to") or []:
        at, email = parse_dt(s["at"]), _norm(s["email"])
        sent[email] = max(at, sent[email]) if email in sent else at
    engaged = {_norm(d) for d in history.get("engaged_domains") or []} - {""}
    open_threads = {_norm(d): {_norm(e) for e in emails} for d, emails in (history.get("open_threads_by_domain") or {}).items()}
    batch: list[tuple[str, str]] = []  # (email, domain) of candidates allowed earlier in this batch
    results = []
    for c in inp["candidates"]:
        email = _norm(c.get("email"))
        local, _, domain = email.partition("@")
        company_domain = _norm((c.get("company") or {}).get("domain"))
        reasons = []
        if not email or c.get("email_status") != "verified":
            reasons.append("email_not_verified")
        if email and not _under(domain, company_domain):
            reasons.append("email_off_company_domain")
        if local in ROLE_MAILBOXES:
            reasons.append("role_mailbox")
        if _blocked(email, company_domain, suppressed):
            reasons.append("suppressed")
        if _blocked(email, company_domain, seeded):
            reasons.append("already_contacted")
        if any(_under(d, x) for d in (domain, company_domain) if d for x in excluded):
            reasons.append("domain_excluded")
        if _norm(c.get("country")) not in allowed_countries:
            reasons.append("country_not_allowed")
        if not title_matches_buyer(c.get("title"), c.get("segment") or ""):
            reasons.append("title_not_buyer")
        if email and ((email in sent and now - sent[email] < COOLDOWN) or any(email == e for e, _ in batch)):
            reasons.append("contact_in_cooldown")
        company_open = {e for d, es in open_threads.items() if _under(d, company_domain) for e in es}
        if company_domain and (company_open - {email} or any(_under(d, company_domain) for e, d in batch if e != email)):
            reasons.append("company_has_active_sequence")
        reached = {e for e, at in sent.items() if now - at < COOLDOWN and _under(e.rpartition("@")[2], company_domain)}
        reached |= company_open | {e for e, d in batch if _under(d, company_domain)}
        if company_domain and email not in reached and len(reached) >= MAX_CONTACTS_PER_COMPANY:
            reasons.append("company_contact_limit")
        if company_domain and any(_under(company_domain, d) or _under(d, company_domain) for d in engaged):
            reasons.append("company_already_engaged")
        if not reasons:
            batch.append((email, company_domain))
        results.append({"email": c.get("email"), "allowed": not reasons, "reasons": reasons})
    return {"results": results}
