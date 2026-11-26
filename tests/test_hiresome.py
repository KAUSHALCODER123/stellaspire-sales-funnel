import io
import json

import pytest

from sslib import hiresome as hs


def fake_urlopen(routes, seen):
    def urlopen(req, timeout=0):
        seen.append((req.full_url, req.headers.get("Authorization")))
        path = req.full_url.split("/opi/v1")[1].split("?")[0]
        status = "?" + req.full_url.split("?")[1] if "?" in req.full_url else ""
        body = routes[(path, status.split("&page")[0])] if (path, status.split("&page")[0]) in routes else routes[path]
        return io.BytesIO(json.dumps(body).encode())
    return urlopen


def test_hired_joins_titles_and_sends_bearer(monkeypatch):
    monkeypatch.setenv("HIRESOME_TOKEN", "tok")
    seen = []
    routes = {
        "/applications": {"data": [{"job": "j1", "updatedAt": "2026-10-20T00:00:00Z"},
                                   {"job": "j2", "updatedAt": "2026-10-21T00:00:00Z"}], "total": 2},
        "/jobs": {"data": [{"_id": "j1", "jobTitle": "Backend Engineer"}], "total": 1},
        "/jobs/j2": {"data": {"_id": "j2", "jobTitle": "Account Executive"}},
    }
    monkeypatch.setattr(hs.urllib.request, "urlopen", fake_urlopen(routes, seen))
    out = hs.hiresome({"action": "hired"})
    assert out["hired"] == [{"job_id": "j1", "title": "Backend Engineer", "updated_at": "2026-10-20T00:00:00Z"},
                            {"job_id": "j2", "title": "Account Executive", "updated_at": "2026-10-21T00:00:00Z"}]
    assert all(auth == "Bearer tok" for _, auth in seen)
    assert "stage=Hired" in seen[0][0]


def test_missing_token_and_auth_errors(monkeypatch):
    monkeypatch.delenv("HIRESOME_TOKEN", raising=False)
    with pytest.raises(hs.HiresomeError, match="hiresome_token_missing"):
        hs.hiresome({"action": "ping"})
    monkeypatch.setenv("HIRESOME_TOKEN", "bad")

    def deny(req, timeout=0):
        raise hs.urllib.error.HTTPError(req.full_url, 401, "no", {}, None)
    monkeypatch.setattr(hs.urllib.request, "urlopen", deny)
    with pytest.raises(hs.HiresomeError, match="hiresome_auth"):
        hs.hiresome({"action": "ping"})


def test_unknown_action_is_a_value_error():
    with pytest.raises(ValueError):
        hs.hiresome({"action": "nope"})
