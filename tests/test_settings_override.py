import io
import json

import pytest

import ss
from sslib.calendar_ist import today
from sslib.config import override_path, settings
from sslib.settings_override import load_settings, settings_check

MONDAY = "2026-12-14T09:00:00+05:30"


def test_check_merges_over_base():
    r = settings_check({"overrides": {"paused": True, "mailbox_daily_cap": 10}})
    assert r["ok"] and r["effective"]["paused"] is True and r["effective"]["mailbox_daily_cap"] == 10
    assert r["effective"]["sending_address"] == "nikita_agrawal@stellaspire.in"


@pytest.mark.parametrize("key", ["warmup_start_date", "sending_address", "opt_out_line", "sender_name", "sender_phone"])
def test_disallowed_keys_rejected(key):
    r = settings_check({"overrides": {key: "x"}})
    assert not r["ok"] and key in r["problems"][0]


@pytest.mark.parametrize("o", [
    {"paused": "yes"}, {"send_mode": "auto"}, {"linkedin_doc_url": "http://x.com/d"}, {"linkedin_doc_url": 5},
    {"mailbox_daily_cap": 0}, {"mailbox_daily_cap": 26}, {"mailbox_daily_cap": True},
    {"target_cities": "Pune"}, {"target_cities": [1]}, {"exclude_domains": ["not a domain"]},
    {"when_no_campaign": "never"}, {"alert_email": "nope"}, {"alert_email": "a@b"},
    {"max_companies_researched_per_run": 0}, {"max_companies_researched_per_run": 41}, {"max_companies_researched_per_run": "5"}])
def test_bad_values_rejected(o):
    assert settings_check({"overrides": o})["ok"] is False


@pytest.mark.parametrize("o", [
    {"paused": False}, {"send_mode": "send"}, {"linkedin_doc_url": ""}, {"linkedin_doc_url": "https://docs.example.com/d/1"},
    {"mailbox_daily_cap": 1}, {"mailbox_daily_cap": 25}, {"target_cities": ["Pune"]}, {"exclude_domains": ["example.com"]},
    {"when_no_campaign": "default"}, {"alert_email": "x@y.com"}, {"max_companies_researched_per_run": 40}, {}])
def test_good_values_accepted(o):
    assert settings_check({"overrides": o})["ok"] is True


def test_load_writes_file_and_settings_merge():
    assert not override_path().exists()
    out = load_settings({"overrides": {"send_mode": "dry_run", "alert_email": "x@y.com"}})
    assert override_path().exists() and out["effective"]["send_mode"] == "dry_run"
    s = settings()
    assert s["send_mode"] == "dry_run" and s["alert_email"] == "x@y.com" and s["sender_first_name"] == "Nikita"


def test_empty_overrides_clear_previous():
    load_settings({"overrides": {"paused": True}})
    load_settings({"overrides": {}})
    assert settings()["paused"] is False


def test_today_honours_paused_override():
    assert today({"sent_today": 0, "drafted_today": 0, "followups_due": 0, "now": MONDAY})["paused"] is False
    load_settings({"overrides": {"paused": True}})
    out = today({"sent_today": 0, "drafted_today": 0, "followups_due": 0, "now": MONDAY})
    assert out["paused"] is True


def test_campaign_command_sees_override(config_dir):
    from sslib.campaigns import campaign
    (config_dir / "campaigns.json").write_text('{"campaigns": []}')
    load_settings({"overrides": {"when_no_campaign": "default"}})
    assert campaign({"counts": {}, "new_cap": 5, "now": MONDAY})["default_targeting"] is True


def test_invalid_load_exits_2_and_writes_nothing(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"overrides": {"warmup_start_date": "2020-01-01"}})))
    assert ss.main(["ss.py", "load-settings"]) == 2
    assert "warmup_start_date" in json.loads(capsys.readouterr().out)["error"]
    assert not override_path().exists()
