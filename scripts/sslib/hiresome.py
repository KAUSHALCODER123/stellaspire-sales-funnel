"""Hiresome Open API (urllib only): hired applications joined to their job titles, for the placement proof.

Reads HIRESOME_TOKEN (required) and HIRESOME_BASE_URL (default: Stellaspire's Hiresome) from the environment.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .netblock import blocked_host

DEFAULT_BASE = "https://stellaspire.hiresome.ai/opi/v1"
PAGE = 50


class HiresomeError(Exception):
    pass


def _get(path: str, params: dict | None = None) -> dict:
    token = os.environ.get("HIRESOME_TOKEN", "").strip()
    if not token:
        raise HiresomeError("hiresome_token_missing")
    base = (os.environ.get("HIRESOME_BASE_URL") or DEFAULT_BASE).rstrip("/")
    url = base + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise HiresomeError(blocked_host(exc, urllib.parse.urlsplit(base).hostname or "hiresome") or ("hiresome_auth" if exc.code in (401, 403) else f"hiresome_http_{exc.code}")) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise HiresomeError("hiresome_unreachable") from exc
    if not isinstance(data, dict):
        raise HiresomeError("hiresome_invalid_response")
    return data


def _paged(path: str, params: dict) -> list[dict]:
    rows, page = [], 1
    while True:
        body = _get(path, {**params, "page": page, "limit": PAGE})
        batch, total = body.get("data"), body.get("total", 0)
        if not isinstance(batch, list) or not str(total).isdigit():
            raise HiresomeError("hiresome_invalid_response")
        rows += batch
        if not batch or page * PAGE >= int(total):
            return rows
        page += 1


def _jobs_by_id(job_ids: set[str]) -> dict[str, str]:
    """Job id -> title for every job the applications point at."""
    titles: dict[str, str] = {}
    for params in ({}, {"status": "Closed"}, {"isActive": "false"}):
        for job in _paged("/jobs", params):
            if isinstance(job, dict) and isinstance(job.get("_id"), str):
                titles.setdefault(job["_id"], (job.get("jobTitle") or "").strip())
    for missing in job_ids - titles.keys():  # a hired job may be archived out of every list
        job = _get(f"/jobs/{urllib.parse.quote(missing, safe='')}").get("data")
        if isinstance(job, dict):
            titles[missing] = (job.get("jobTitle") or "").strip()
    return titles


def hiresome(inp: dict) -> dict:
    action = inp["action"]
    if action == "ping":
        body = _get("/jobs", {"page": 1, "limit": 1})
        return {"ok": isinstance(body.get("data"), list), "total_jobs": body.get("total")}
    if action == "hired":
        apps = [a for a in _paged("/applications", {"stage": "Hired"})
                if isinstance(a, dict) and isinstance(a.get("job"), str) and a["job"].strip()]
        titles = _jobs_by_id({a["job"] for a in apps})
        return {"hired": [{"job_id": a["job"], "title": titles.get(a["job"], ""), "updated_at": a.get("updatedAt")}
                          for a in apps if titles.get(a["job"])]}
    raise ValueError(f"unknown hiresome action: {action}")
