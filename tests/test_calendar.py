import builtins
import importlib

from sslib import calendar_ist as cal
from sslib.calendar_ist import next_step, today

ZERO = {"sent_today": 0, "drafted_today": 0, "followups_due": 0}


def day(iso, **extra):
    return today({**ZERO, **extra, "now": f"{iso}T09:00:00+05:30"})


def test_weekday_is_a_send_day_in_week_zero():
    r = day("2026-11-04")  # Wednesday
    assert r["send_day"] and r["reason"] is None and r["warmup_week"] == 0 and r["total_cap"] == 5


def test_weekend_is_not_a_send_day():
    assert day("2026-11-07")["reason"] == "weekend"  # Saturday
    assert not day("2026-11-08")["send_day"]  # Sunday


def test_weekday_public_holiday_is_not_a_send_day():
    r = day("2027-01-26")  # Republic Day, a Tuesday
    assert r["send_day"] is False and r["reason"] == "public_holiday" and r["total_cap"] == 0


def test_now_is_read_in_ist_not_utc():
    # 23:00 UTC Friday is already Saturday morning in India.
    assert today({**ZERO, "now": "2026-11-06T23:00:00+00:00"})["reason"] == "weekend"


def test_empty_warmup_start_blocks_sending(set_settings):
    set_settings(warmup_start_date="")
    r = day("2026-11-04")
    assert r["send_day"] is False and r["reason"] == "warmup_start_date_not_set"


def test_warmup_not_started_yet_blocks_sending(set_settings):
    set_settings(warmup_start_date="2026-12-01")
    assert day("2026-11-04")["reason"] == "before_warmup_start"


def test_paused_setting_blocks_sending(set_settings):
    set_settings(paused=True)
    r = day("2026-11-04")
    assert r["send_day"] is False and r["reason"] == "paused" and r["paused"] is True


def test_missing_holidays_package_never_sends(monkeypatch):
    monkeypatch.setattr(cal, "country_holidays", None)  # what a failed `import holidays` leaves behind
    r = day("2026-11-04")
    assert r["send_day"] is False and r["reason"] == "holidays_package_missing"


def test_import_failure_of_holidays_is_handled(monkeypatch):
    real = builtins.__import__

    def fail(name, *a, **k):
        if name == "holidays":
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fail)
    try:
        fresh = importlib.reload(cal)
        assert fresh.country_holidays is None
        assert fresh.today({**ZERO, "now": "2026-11-04T09:00:00+05:30"})["reason"] == "holidays_package_missing"
    finally:
        monkeypatch.undo()
        importlib.reload(cal)


def test_ramp_by_full_weeks():
    caps = [day(d)["total_cap"] for d in ("2026-11-04", "2026-11-11", "2026-11-18", "2026-11-25", "2026-12-16")]
    assert caps == [5, 10, 15, 20, 20]
    assert day("2026-11-25")["warmup_week"] == 3


def test_cap_never_exceeds_mailbox_cap(set_settings):
    set_settings(mailbox_daily_cap=12)
    assert day("2026-11-25")["total_cap"] == 12


def test_followups_are_served_first_then_new():
    r = day("2026-11-25", sent_today=2, followups_due=4)  # week 3: cap 20
    assert (r["total_cap"], r["followup_cap"], r["new_cap"]) == (20, 4, 14)


def test_new_cap_floors_at_zero_and_followups_are_capped():
    r = day("2026-11-04", sent_today=3, drafted_today=1, followups_due=6)  # cap 5, 1 left
    assert (r["followup_cap"], r["new_cap"]) == (1, 0)


def thread(step, last, **extra):
    return {"thread_id": f"t{step}", "step": step, "last_sent_at": f"{last}T10:00:00+05:30",
            "replied": False, "stopped": False, **extra}


def due(threads, iso):
    return next_step({"threads": threads, "now": f"{iso}T08:00:00+05:30"})


def test_business_day_counting_skips_weekend_and_holiday():
    # Sent Thu 2027-01-21; step 2 -> 3 waits 4 business days (STEP_DELAYS_DAYS[2]): Fri 22, Mon 25, (Tue 26 holiday),
    # Wed 27, Thu 28.
    t = [thread(2, "2027-01-21")]
    assert due(t, "2027-01-27")["due"] == []
    assert due(t, "2027-01-28")["due"] == [{"thread_id": "t2", "next_step": 3}]


def test_holiday_and_weekend_both_push_the_due_date():
    # Step 1 -> 2 waits 3 business days. Sent Fri 2027-01-22: Mon 25, (Tue 26 holiday), Wed 27, Thu 28.
    t = [thread(1, "2027-01-22")]
    assert due(t, "2027-01-27")["due"] == []
    assert due(t, "2027-01-28")["due"][0]["next_step"] == 2


def test_second_email_follows_three_business_days_after_the_first():
    t = [thread(1, "2026-11-06")]  # Friday: Mon 9, Tue 10, Wed 11
    assert due(t, "2026-11-10")["due"] == []
    assert due(t, "2026-11-11")["due"][0]["next_step"] == 2


def test_replied_and_stopped_threads_are_never_due():
    t = [thread(1, "2026-11-02", replied=True), thread(1, "2026-11-02", stopped=True, thread_id="x")]
    assert due(t, "2026-12-01") == {"due": [], "finished": []}


def test_step_five_threads_are_finished_not_due():
    assert due([thread(5, "2026-11-02")], "2026-12-01") == {"due": [], "finished": ["t5"]}


def test_research_budget_is_capped_and_zero_without_new_cap(set_settings):
    r = day("2026-11-25")  # cap 20, all new
    assert r["new_cap"] == 20 and r["research_budget"] == 15
    r = day("2026-11-04")  # cap 5 -> 5 * 3 = 15
    assert r["research_budget"] == 15
    set_settings(max_companies_researched_per_run=6)
    assert day("2026-11-04", sent_today=3)["research_budget"] == 6  # min(6, 2*3)
    set_settings(max_companies_researched_per_run=15)
    assert day("2026-11-04", sent_today=4)["research_budget"] == 3
    assert day("2026-11-04", sent_today=5)["research_budget"] == 0
    assert day("2026-11-07")["research_budget"] == 0  # weekend


def test_pending_drafts_hold_blocks_new_and_followups():
    r = day("2026-11-04", pending_drafts=5, followups_due=2)  # cap 5
    assert r["send_day"] is True and r["hold_reason"] == "drafts_waiting"
    assert (r["new_cap"], r["followup_cap"], r["research_budget"]) == (0, 0, 0)


def test_pending_drafts_hold_off_below_cap():
    r = day("2026-11-04", pending_drafts=4, followups_due=1)
    assert r["new_cap"] == 4
    assert r["hold_reason"] is None and r["followup_cap"] == 1
    r = day("2026-11-04")
    assert r["hold_reason"] is None and r["stale_drafts"] is False


def test_hold_not_reported_on_a_non_send_day():
    r = day("2026-11-07", pending_drafts=9)
    assert r["send_day"] is False and r["hold_reason"] is None


def test_stale_draft_boundary_across_a_weekend():
    # draft made Friday 2026-11-06: 2 business days later is Tuesday 11-10
    old = "2026-11-06T10:00:00+05:30"
    assert day("2026-11-09", pending_drafts=1, oldest_pending_draft_at=old)["stale_drafts"] is False  # Mon
    assert day("2026-11-10", pending_drafts=1, oldest_pending_draft_at=old)["stale_drafts"] is False  # Tue
    assert day("2026-11-11", pending_drafts=1, oldest_pending_draft_at=old)["stale_drafts"] is True   # Wed
    assert day("2026-11-11", pending_drafts=0, oldest_pending_draft_at=None)["stale_drafts"] is False
