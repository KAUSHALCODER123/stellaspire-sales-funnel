"""Apollo API calls (urllib only), trimmed to the fields the engine's pipeline.py uses.

The key is sent as X-Api-Key only when APOLLO_API_KEY is set; in the cloud a network proxy attaches it.
"""
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .calendar_ist import now_ist
from .netblock import blocked_host

BASE = "https://api.apollo.io/api/v1"
ORG_FIELDS = ("id", "name", "primary_domain", "website_url", "industry", "estimated_num_employees", "city", "country",
              "linkedin_url", "naics_codes", "sic_codes")
JOB_FIELDS = ("id", "title", "city", "state", "country", "url", "posted_at")
PERSON_FIELDS = ("id", "name", "first_name", "last_name", "title", "email", "email_status", "country", "linkedin_url")


class ApolloError(Exception):
    pass


def _request(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
    url = BASE + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    if key := os.environ.get("APOLLO_API_KEY"):
        headers["X-Api-Key"] = key
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise ApolloError(blocked_host(exc, "api.apollo.io") or ("apollo_auth" if exc.code in (401, 403) else f"apollo_http_{exc.code}")) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ApolloError("apollo_unreachable") from exc
    if not isinstance(data, dict):
        raise ApolloError("apollo_invalid_response")
    return data


def _state_dir() -> Path:
    return Path(os.environ.get("SS_STATE_DIR") or Path(tempfile.gettempdir()) / "stellaspire-outreach")


def _counter_path(inp: dict) -> Path:
    return _state_dir() / f"apollo-{now_ist(inp.get('now')).date().isoformat()}.json"


def _load(path: Path) -> dict:
    try:
        calls = json.loads(path.read_text(encoding="utf-8")).get("calls", {})
        return {k: int(v) for k, v in calls.items()}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def _count(inp: dict, action: str, n: int = 1) -> None:
    """Add n to today's per-action call count. Reporting only: it never blocks a call or fails the run."""
    try:
        path = _counter_path(inp)
        calls = _load(path)
        calls[action] = calls.get(action, 0) + n
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"calls": calls}), encoding="utf-8")
    except (OSError, ValueError):
        pass


def _usage(inp: dict) -> dict:
    calls = _load(_counter_path(inp))
    try:
        reported = _request("POST", "/usage_stats/api_usage_stats")
    except Exception:  # not permitted, offline, anything: usage is best effort
        reported = None
    return {"calls": calls, "credits_used_this_run": calls.get("match_person", 0) + calls.get("reveal", 0),
            "apollo_reported": reported}


def _trim(rows, fields: tuple[str, ...]) -> list[dict]:
    if not isinstance(rows, list):
        raise ApolloError("apollo_invalid_response")
    return [{k: r.get(k) for k in fields} for r in rows if isinstance(r, dict)]


def apollo(inp: dict) -> dict:
    action = inp["action"]
    if action == "usage":
        return _usage(inp)
    if action in ("search_orgs", "job_postings", "search_people"):
        _count(inp, action)
    if action == "search_orgs":
        lo, hi = inp["headcount"]
        res = _request("POST", "/mixed_companies/search", {
            "q_organization_keyword_tags": inp["keywords"], "organization_locations": inp["locations"],
            "organization_num_employees_ranges": [f"{lo},{hi}"], "page": inp.get("page", 1),
            "per_page": inp.get("per_page", 25)})
        return {"organizations": _trim(res.get("organizations", []) + res.get("accounts", []), ORG_FIELDS)}
    if action == "job_postings":
        res = _request("GET", f"/organizations/{urllib.parse.quote(str(inp['organization_id']), safe='')}/job_postings")
        return {"job_postings": _trim(res.get("organization_job_postings"), JOB_FIELDS)}
    if action == "search_people":
        res = _request("POST", "/mixed_people/api_search", {
            "organization_ids": [inp["organization_id"]], "person_titles": inp["titles"],
            "per_page": inp.get("per_page", 10), "page": 1})
        return {"people": _trim(res.get("people", []), PERSON_FIELDS)}
    if action == "reveal":  # spends one credit per id; the only call that returns email + email_status for a search hit
        _count(inp, "reveal", len(inp["person_ids"]))
        res = _request("POST", "/people/bulk_match", {"details": [{"id": i} for i in inp["person_ids"]],
                                                       "reveal_personal_emails": False})
        return {"people": _trim(res.get("matches", []), PERSON_FIELDS)}
    if action == "match_person":  # spends one credit
        _count(inp, "match_person")
        body = {"first_name": inp["first_name"], "last_name": inp["last_name"], "domain": inp["domain"],
                "reveal_personal_emails": False, "reveal_phone_number": False}
        if inp.get("linkedin_url"):
            body["linkedin_url"] = inp["linkedin_url"]
        person = _request("POST", "/people/match", body).get("person")
        return {"person": _trim([person], PERSON_FIELDS)[0] if isinstance(person, dict) else None}
    raise ValueError(f"unknown apollo action: {action}")
