from sslib.roles import FAMILIES, buyer_rank, classify_title, is_hireable, role_check, title_matches_buyer

NOW = "2026-11-26T10:00:00+05:30"


def check(posted_at, on_board=True, status="active", title="Data Engineer"):
    return role_check({"title": title, "posted_at": posted_at, "on_employer_board": on_board, "status": status, "now": NOW})


def test_recent_role_on_the_board_is_fresh():
    r = check("2026-11-10T00:00:00+05:30")
    assert r["fresh"] and r["reason"] is None and r["age_days"] == 16
    assert r["family"] == "tech_ai_data" and r["hireable"]


def test_31_days_old_on_the_board_is_stale():
    assert check("2026-10-26T09:00:00+05:30")["reason"] == "stale"  # 31 days


def test_exactly_30_days_old_is_fresh():
    assert check("2026-10-27T10:00:00+05:30")["fresh"]


def test_apollo_only_limit_is_14_days():
    assert check("2026-11-11T09:00:00+05:30", on_board=False)["reason"] == "stale"  # 15 days
    assert check("2026-11-12T10:00:00+05:30", on_board=False)["fresh"]  # 14 days


def test_future_dated_is_not_fresh():
    r = check("2026-11-27T00:00:00+05:30")
    assert not r["fresh"] and r["reason"] == "future_dated"


def test_undated_is_not_fresh():
    r = check(None)
    assert r["reason"] == "undated" and r["age_days"] is None


def test_closed_wins():
    assert check("2026-11-20T00:00:00+05:30", status="closed")["reason"] == "closed"


def test_bare_date_is_accepted():
    assert check("2026-11-20")["fresh"]
    assert check("2026-11-27")["reason"] == "future_dated"


def test_interns_are_not_hireable():
    r = check("2026-11-20", title="Software Engineering Intern")
    assert not r["hireable"] and not r["fresh"]


def test_unclassified_title_has_no_family():
    assert check("2026-11-20", title="Zookeeper")["family"] is None


def test_classification_and_buyers_match_the_engine():
    assert classify_title("Firmware Engineer") == "hardware_robotics"
    assert classify_title("Sales Development Rep") == "growth"
    assert classify_title("") == "other"
    assert is_hireable("Backend Developer") and not is_hireable("Trainee Analyst")
    assert buyer_rank("Head of Talent Acquisition", "tech_ai_data") == 5
    assert title_matches_buyer("Co-Founder & CEO", "growth")
    assert not title_matches_buyer("Intern", "growth") and not title_matches_buyer(None, "growth")
    assert set(FAMILIES) >= {"tech_ai_data", "growth", "bfsi"}
