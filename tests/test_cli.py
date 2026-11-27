import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

import ss
from sslib import apollo as apollo_mod

SS = Path(__file__).resolve().parents[1] / "scripts" / "ss.py"


def run(cmd, payload, raw=None):
    p = subprocess.run([sys.executable, str(SS), cmd], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def test_round_trip_json():
    code, out = run("today", {"sent_today": 0, "drafted_today": 0, "followups_due": 0, "now": "2026-11-04T09:00:00+05:30"})
    assert code == 0 and out["send_day"] is True and out["total_cap"] == 5


def test_invalid_json_exits_2():
    code, out = run("today", None, raw="{not json")
    assert code == 2 and "error" in out


def test_missing_key_exits_2():
    code, out = run("health", {"sent_14d": 1})
    assert code == 2 and "bounced_14d" in out["error"]


def test_non_object_exits_2():
    assert run("today", [1, 2])[0] == 2


def test_unknown_command_exits_2():
    assert run("nope", {})[0] == 2


def test_every_command_is_dispatched():
    assert set(ss.COMMANDS) == {"today", "role-check", "check-contacts", "fit", "proof", "facts", "check-email",
                                "check-linkedin", "compose", "next-step", "health", "apollo", "hiresome", "campaign", "imported-leads",
                                "campaign-check", "settings-check", "load-settings"}


def test_scripts_do_not_write_to_config(config_dir):
    before = {p.name: p.read_bytes() for p in config_dir.iterdir()}
    run("check-contacts", {"candidates": []})
    assert before == {p.name: p.read_bytes() for p in config_dir.iterdir()}


# --- apollo (urllib is mocked; no network)
class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def capture(monkeypatch, payload=None, error=None):
    seen = {}

    def fake(req, timeout):
        seen["req"] = req
        if error:
            raise error
        return FakeResponse(json.dumps(payload).encode())

    monkeypatch.setattr(apollo_mod.urllib.request, "urlopen", fake)
    return seen


def test_apollo_trims_orgs_and_sends_key_only_when_set(monkeypatch):
    seen = capture(monkeypatch, {"organizations": [{"id": "o1", "name": "Acme", "junk": 1}], "accounts": []})
    monkeypatch.delenv("APOLLO_API_KEY", raising=False)
    out = apollo_mod.apollo({"action": "search_orgs", "keywords": ["saas"], "locations": ["Pune, India"], "headcount": [30, 500]})
    assert out["organizations"][0]["id"] == "o1" and "junk" not in out["organizations"][0]
    assert "X-api-key" not in seen["req"].headers
    assert json.loads(seen["req"].data)["organization_num_employees_ranges"] == ["30,500"]
    monkeypatch.setenv("APOLLO_API_KEY", "k")
    apollo_mod.apollo({"action": "search_orgs", "keywords": [], "locations": [], "headcount": [1, 2]})
    assert seen["req"].headers["X-api-key"] == "k"


def test_apollo_job_postings_people_and_match(monkeypatch):
    capture(monkeypatch, {"organization_job_postings": [{"id": "j", "title": "SDR", "posted_at": "2026-11-01", "x": 1}]})
    assert apollo_mod.apollo({"action": "job_postings", "organization_id": "o1"})["job_postings"][0]["title"] == "SDR"
    capture(monkeypatch, {"people": [{"id": "p", "title": "CTO", "zzz": 1}]})
    assert apollo_mod.apollo({"action": "search_people", "organization_id": "o1", "titles": ["CTO"]})["people"][0]["id"] == "p"
    capture(monkeypatch, {"matches": [{"id": "p", "email": "a@b.in", "email_status": "verified"}]})
    assert apollo_mod.apollo({"action": "reveal", "person_ids": ["p"]})["people"][0]["email"] == "a@b.in"
    capture(monkeypatch, {"person": {"id": "p", "email": "a@b.in"}})
    r = apollo_mod.apollo({"action": "match_person", "first_name": "A", "last_name": "B", "domain": "b.in"})
    assert r["person"]["email"] == "a@b.in"
    capture(monkeypatch, {})
    assert apollo_mod.apollo({"action": "match_person", "first_name": "A", "last_name": "B", "domain": "b.in"})["person"] is None


@pytest.mark.parametrize("code", [401, 403])
def test_apollo_auth_failure_is_a_clear_error(monkeypatch, code):
    capture(monkeypatch, error=urllib.error.HTTPError("u", code, "no", {}, None))
    with pytest.raises(apollo_mod.ApolloError, match="apollo_auth"):
        apollo_mod.apollo({"action": "job_postings", "organization_id": "o1"})


def test_apollo_auth_failure_through_the_cli(monkeypatch, capsys):
    capture(monkeypatch, error=urllib.error.HTTPError("u", 401, "no", {}, None))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"action": "job_postings", "organization_id": "o1"})))
    assert ss.main(["ss.py", "apollo"]) == 1
    assert json.loads(capsys.readouterr().out) == {"error": "apollo_auth"}


def test_unknown_apollo_action_is_an_input_error():
    with pytest.raises(ValueError):
        apollo_mod.apollo({"action": "delete_everything"})


# --- apollo usage counter (counter file in SS_STATE_DIR; HTTP mocked; reporting only, never blocks)

def _fake_apollo(monkeypatch, usage=None):
    calls = []

    def fake(method, path, body=None, params=None):
        calls.append(path)
        if path.endswith("api_usage_stats"):
            if usage is None:
                raise apollo_mod.ApolloError("apollo_auth")
            return usage
        return {"person": {"id": "p"}, "matches": [{"id": "p"}], "organizations": [], "people": [],
                "organization_job_postings": []}
    monkeypatch.setattr(apollo_mod, "_request", fake)
    return calls


MATCH = {"action": "match_person", "first_name": "A", "last_name": "B", "domain": "b.in"}


def test_apollo_usage_counts_calls_by_action_and_credits(monkeypatch):
    _fake_apollo(monkeypatch)
    assert apollo_mod.apollo({"action": "usage"}) == {"calls": {}, "credits_used_this_run": 0, "apollo_reported": None}
    apollo_mod.apollo(MATCH)
    apollo_mod.apollo(MATCH)
    apollo_mod.apollo({"action": "reveal", "person_ids": ["a", "b", "c"]})  # one credit per id
    apollo_mod.apollo({"action": "search_people", "organization_id": "o", "titles": []})
    apollo_mod.apollo({"action": "job_postings", "organization_id": "o"})
    apollo_mod.apollo({"action": "search_orgs", "keywords": [], "locations": [], "headcount": [1, 2]})
    out = apollo_mod.apollo({"action": "usage"})
    assert out["calls"] == {"match_person": 2, "reveal": 3, "search_people": 1, "job_postings": 1, "search_orgs": 1}
    assert out["credits_used_this_run"] == 5


def test_apollo_never_blocks_calls(monkeypatch):
    calls = _fake_apollo(monkeypatch)
    for _ in range(60):
        assert "error" not in apollo_mod.apollo(MATCH)
    assert len(calls) == 60


def test_apollo_usage_returns_apollos_own_report_when_available(monkeypatch):
    _fake_apollo(monkeypatch, usage={"/people/match": {"day": {"limit": 100, "consumed": 4}}})
    assert apollo_mod.apollo({"action": "usage"})["apollo_reported"] == {"/people/match": {"day": {"limit": 100, "consumed": 4}}}


def test_apollo_usage_survives_a_failing_usage_endpoint_and_bad_state_dir(monkeypatch, tmp_path):
    _fake_apollo(monkeypatch)
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("SS_STATE_DIR", str(blocker / "sub"))  # cannot be created
    apollo_mod.apollo(MATCH)  # counting fails silently
    assert apollo_mod.apollo({"action": "usage"})["apollo_reported"] is None


def test_apollo_counter_is_per_ist_day(monkeypatch):
    _fake_apollo(monkeypatch)
    apollo_mod.apollo({**MATCH, "now": "2026-11-04T09:00:00+05:30"})
    assert apollo_mod.apollo({"action": "usage", "now": "2026-11-04T20:00:00+05:30"})["credits_used_this_run"] == 1
    assert apollo_mod.apollo({"action": "usage", "now": "2026-11-05T09:00:00+05:30"})["credits_used_this_run"] == 0


def test_apollo_usage_through_the_cli(monkeypatch, capsys):
    _fake_apollo(monkeypatch)
    monkeypatch.setattr(ss.sys, "stdin", io.StringIO(json.dumps({"action": "usage"})))
    assert ss.main(["ss.py", "apollo"]) == 0
    assert json.loads(capsys.readouterr().out)["credits_used_this_run"] == 0


def test_apollo_sandbox_block_is_reported_as_network_blocked(monkeypatch):
    import io
    def refused(req, timeout=0):
        raise apollo_mod.urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b"HTTP 403, host not allowed for this session"))
    monkeypatch.setattr(apollo_mod.urllib.request, "urlopen", refused)
    with pytest.raises(apollo_mod.ApolloError, match="network_blocked:api.apollo.io"):
        apollo_mod.apollo({"action": "search_orgs", "keywords": [], "locations": [], "headcount": [1, 2]})
