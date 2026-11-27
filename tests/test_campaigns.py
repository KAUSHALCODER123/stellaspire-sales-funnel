import json

import pytest

from sslib.campaigns import campaign

NOW = "2026-12-10T09:00:00+05:30"


def camp(slug, **kw):
    base = {"slug": slug, "name": slug.title(), "status": "active", "families": ["tech_ai_data"], "cities": ["Pune"],
            "industries": [], "headcount": [50, 500], "target_contacts": 50, "start_date": "2026-12-01", "priority": 1}
    return {**base, **kw}


@pytest.fixture
def setup(config_dir):
    def apply(*campaigns):
        (config_dir / "campaigns.json").write_text(json.dumps({"campaigns": list(campaigns)}))
    return apply


def run(counts=None, new_cap=10, now=NOW):
    return campaign({"counts": counts or {}, "new_cap": new_cap, "now": now})


def test_shipped_example_is_draft_and_inert():
    out = run(now="2026-11-28T09:00:00+05:30")
    slugs = [c["slug"] for c in out["active"]]
    assert slugs == ["existing-leads"] and out["completed"] == [] and out["waiting_for_campaign"] is False


def test_draft_ignored(setup):
    setup(camp("a", status="draft"))
    assert run()["active"] == []


def test_before_start_date_ignored(setup):
    setup(camp("a", start_date="2026-12-11"))
    out = run()
    assert out["active"] == [] and out["completed"] == []


def test_target_reached_completes(setup):
    setup(camp("a", target_contacts=20))
    out = run({"a": {"contacted": 20, "active_threads": 3, "replied": 2, "interested": 1}})
    assert out["active"] == []
    c = out["completed"][0]
    assert c["reason"] == "target_reached" and c["all_sequences_finished"] is False
    assert c["results"]["reply_rate"] == 0.1 and c["results"]["interested_rate"] == 0.05


def test_end_date_passed_completes(setup):
    setup(camp("a", end_date="2026-12-09"))
    c = run({"a": {"contacted": 5}})["completed"][0]
    assert c["reason"] == "end_date_passed" and c["all_sequences_finished"] is True


def test_end_date_today_still_active(setup):
    setup(camp("a", end_date="2026-12-10"))
    assert run()["active"][0]["slug"] == "a"


def test_quota_split_by_priority_capped_by_remaining(setup):
    setup(camp("low", priority=1), camp("high", priority=5, target_contacts=10))
    out = run({"high": {"contacted": 6}}, new_cap=10)
    assert [a["slug"] for a in out["active"]] == ["high", "low"]
    assert out["active"][0]["remaining"] == 4 and out["active"][0]["quota_today"] == 4
    assert out["active"][1]["quota_today"] == 6
    assert out["default_targeting"] is False and out["waiting_for_campaign"] is False


def test_leftover_not_given_to_default_when_campaign_active(setup, set_settings):
    set_settings(when_no_campaign="default")
    setup(camp("a", target_contacts=3))
    out = run(new_cap=10)
    assert out["active"][0]["quota_today"] == 3
    assert out["default_targeting"] is False and out["waiting_for_campaign"] is False


def test_no_active_campaigns_wait_is_default(setup):
    setup(camp("a", status="paused"))
    out = run()
    assert out["active"] == [] and out["default_targeting"] is False and out["waiting_for_campaign"] is True


def test_no_active_campaigns_default_mode(setup, set_settings):
    set_settings(when_no_campaign="default")
    setup(camp("a", status="paused"))
    out = run()
    assert out["default_targeting"] is True and out["waiting_for_campaign"] is False


def test_completed_campaign_waits_when_nothing_else_active(setup):
    setup(camp("a", target_contacts=1))
    out = run({"a": {"contacted": 1}})
    assert out["waiting_for_campaign"] is True and out["completed"][0]["slug"] == "a"


def test_bad_when_no_campaign_rejected(setup, set_settings):
    set_settings(when_no_campaign="auto")
    with pytest.raises(ValueError):
        run()


def test_zero_contacted_rates_are_null(setup):
    setup(camp("a", end_date="2026-12-01"))
    r = run()["completed"][0]["results"]
    assert r["reply_rate"] is None and r["interested_rate"] is None


def test_bad_slug_rejected(setup):
    setup(camp("Bad Slug"))
    with pytest.raises(ValueError):
        run()


def run_with(gmail, new_cap=10):
    return campaign({"campaigns": gmail, "counts": {}, "new_cap": new_cap, "now": NOW})


def test_gmail_overrides_config_by_slug(setup):
    setup(camp("a", target_contacts=50))
    assert run_with([camp("a", target_contacts=7)])["active"][0]["remaining"] == 7


def test_gmail_only_campaign_appears(setup):
    setup(camp("a", status="paused"))
    assert [a["slug"] for a in run_with([camp("b")])["active"]] == ["b"]


def test_gmail_pause_overrides_active_config(setup):
    setup(camp("a"))
    assert run_with([camp("a", status="paused")])["active"] == []


def test_invalid_gmail_entry_exits_2_naming_slug(capsys, monkeypatch):
    import io

    import ss
    bad = camp("pune-sales", target_contacts=0)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"campaigns": [bad], "new_cap": 5})))
    assert ss.main(["ss.py", "campaign"]) == 2
    assert "pune-sales" in json.loads(capsys.readouterr().out)["error"]


def check(c, existing=(), **extra):
    from sslib.campaigns import campaign_check
    return campaign_check({"campaign": c, "existing_slugs": list(existing), "now": NOW, **extra})


def good(**kw):
    return {"slug": "pune-sales", "name": "Pune sales", "families": ["growth"], "cities": ["Pune"],
            "headcount": [50, 200], "target_contacts": 40, **kw}


def test_check_fills_defaults():
    r = check(good())
    assert r["ok"] is True and r["problems"] == []
    n = r["normalized"]
    assert n["priority"] == 1 and n["status"] == "draft" and n["start_date"] == "2026-12-10"


def test_check_keeps_given_values():
    n = check(good(priority=3, status="active", start_date="2026-12-15"))["normalized"]
    assert (n["priority"], n["status"], n["start_date"]) == (3, "active", "2026-12-15")


def test_check_unknown_family_lists_valid_keys():
    r = check(good(families=["sales"]))
    assert r["ok"] is False and "tech_ai_data" in r["problems"][0] and "(" in r["problems"][0]


@pytest.mark.parametrize("hc", [[200, 50], [50, 50], [50], "50-200", None])
def test_check_bad_headcount(hc):
    assert check(good(headcount=hc))["ok"] is False


@pytest.mark.parametrize("t", [0, 2001, "40", True])
def test_check_bad_target(t):
    assert check(good(target_contacts=t))["ok"] is False


def test_check_target_bounds_ok():
    assert check(good(target_contacts=2000))["ok"] and check(good(target_contacts=1))["ok"]


def test_check_end_before_start():
    assert not check(good(start_date="2026-12-15", end_date="2026-12-15"))["ok"]
    assert check(good(start_date="2026-12-15", end_date="2026-12-16"))["ok"]


def test_check_duplicate_slug_unless_update():
    assert not check(good(), existing=["pune-sales"])["ok"]
    assert check(good(), existing=["pune-sales"], update=True)["ok"]


def test_check_bad_slug_and_status():
    assert not check(good(slug="Pune Sales"))["ok"]
    assert not check(good(status="live"))["ok"]
