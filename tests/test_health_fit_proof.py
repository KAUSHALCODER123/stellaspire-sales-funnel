from sslib.fit import fit, priority, score_fit
from sslib.health import health
from sslib.proof import facts, proof

NOW = "2026-11-26T10:00:00+05:30"


# --- health
def test_one_bounce_in_forty_is_fine():
    assert health({"sent_14d": 40, "bounced_14d": 1, "complaints": 0}) == {"pause": False, "reason": None}


def test_bounce_rate_over_three_percent_pauses():
    r = health({"sent_14d": 20, "bounced_14d": 1, "complaints": 0})  # 5%
    assert r["pause"] and r["reason"].startswith("bounce_rate")


def test_three_percent_exactly_does_not_pause():
    assert not health({"sent_14d": 100, "bounced_14d": 3, "complaints": 0})["pause"]


def test_under_twenty_sends_never_pause_on_bounces():
    assert not health({"sent_14d": 19, "bounced_14d": 5, "complaints": 0})["pause"]


def test_any_complaint_pauses():
    assert health({"sent_14d": 5, "bounced_14d": 0, "complaints": 1}) == {"pause": True, "reason": "spam_complaint"}


def test_paused_setting_pauses(set_settings):
    set_settings(paused=True)
    assert health({"sent_14d": 0, "bounced_14d": 0, "complaints": 0})["pause"]


# --- fit
BRIEF = {"employee_estimate": 120, "industry_match": "exact", "india_presence": True,
         "buyer_titles_found": ["CTO"], "disqualifier": "none"}


def test_best_fit_scores_ten_and_is_p0_with_a_signal():
    f = score_fit(BRIEF, "tech_ai_data")
    assert f == {"industry": 3, "size": 3, "size_verified": True, "persona": 2, "clean": 2, "total": 10}
    assert priority(f, BRIEF, 1, 1, ["india"]) == "P0"
    assert priority(f, BRIEF, 3, 0, ["india"]) == "P0"
    assert priority(f, BRIEF, 1, 0, ["india"]) == "P1"


def test_hard_disqualifier_is_dq_and_soft_costs_clean_points():
    hard = {**BRIEF, "disqualifier": "staffing_agency"}
    assert priority(score_fit(hard, "tech_ai_data"), hard, 5, 5, ["india"]) == "DQ"
    soft = score_fit({**BRIEF, "disqualifier": "recent_layoffs"}, "tech_ai_data")
    assert soft["clean"] == 1


def test_size_bands_and_unknown_size():
    assert score_fit({**BRIEF, "employee_estimate": 20}, "tech_ai_data")["size"] == 1  # 15..750 near band
    assert score_fit({**BRIEF, "employee_estimate": 5000}, "tech_ai_data")["size"] == 0
    assert score_fit({**BRIEF, "employee_estimate": 0}, "tech_ai_data")["size_verified"] is False


def test_outside_allowed_country_is_dq():
    b = {**BRIEF, "india_presence": False, "hq_country": "Germany"}
    assert priority(score_fit(b, "tech_ai_data"), b, 3, 1, ["india"]) == "DQ"
    b = {**BRIEF, "india_presence": False, "hq_country": "India"}
    assert priority(score_fit(b, "tech_ai_data"), b, 3, 1, ["india"]) == "P0"


def test_fit_command_wraps_both():
    r = fit({"brief": BRIEF, "family": "tech_ai_data", "roles": 3, "signals": 0})
    assert r["priority"] == "P0" and r["fit"]["total"] == 10


def test_fit_rejects_unknown_family():
    import pytest
    with pytest.raises(ValueError):
        fit({"brief": BRIEF, "family": "nope", "roles": 1, "signals": 0})


# --- proof
def hired(job_id, title, at):
    return {"job_id": job_id, "title": title, "updated_at": at}


def test_role_match_counts_recent_hires():
    rows = [hired("j1", "Senior Data Engineer", "2026-11-01T00:00:00Z"),
            hired("j2", "Data Engineer", "2026-10-10T00:00:00Z"),
            hired("j3", "Data Engineer", "2026-01-10T00:00:00Z"),
            hired("j4", "Sales Executive", "2026-11-01T00:00:00Z")]
    r = proof({"role": "Data Engineer", "family": "tech_ai_data", "hired": rows, "now": NOW})
    assert r["proof"] == "We recently filled 2 Data Engineer roles."
    assert r["basis"]["scope"] == "role" and r["basis"]["hired_applications"] == 3
    assert r["basis"]["recently_updated"] == 2


def test_all_time_wording_when_nothing_is_recent():
    rows = [hired("j1", "Data Engineer", "2025-01-10T00:00:00Z")]
    r = proof({"role": "Data Engineer", "family": "tech_ai_data", "hired": rows, "now": NOW})
    assert r["proof"] == "We have filled 1 Data Engineer role."


def test_missing_and_future_dates_are_never_recent():
    rows = [hired("j1", "Data Engineer", None), hired("j2", "Data Engineer", "2027-01-01T00:00:00Z")]
    r = proof({"role": "Data Engineer", "family": "tech_ai_data", "hired": rows, "now": NOW})
    assert r["proof"].startswith("We have filled 2") and r["basis"]["undated"] == 1 and r["basis"]["future_dated"] == 1


def test_family_fallback_uses_the_family_label():
    rows = [hired("j1", "Backend Developer", "2026-11-01T00:00:00Z")]
    r = proof({"role": "ML Scientist", "family": "tech_ai_data", "hired": rows, "now": NOW})
    assert r["proof"] == "We recently filled 1 software, AI and data engineering role."
    assert r["basis"]["scope"] == "family"


def test_no_matching_hires_gives_no_proof():
    r = proof({"role": "Data Engineer", "family": "tech_ai_data", "hired": [hired("j", "Sales Executive", NOW)], "now": NOW})
    assert r == {"proof": None, "basis": {}}
    assert proof({"role": "x", "family": "tech_ai_data", "hired": [], "now": NOW})["proof"] is None


def test_several_hires_on_one_posting_count_once_each_but_one_posting():
    rows = [hired("j1", "Data Engineer", "2026-11-01T00:00:00Z"), hired("j1", "Data Engineer", "2026-11-02T00:00:00Z")]
    r = proof({"role": "Data Engineer", "family": "tech_ai_data", "hired": rows, "now": NOW})
    assert r["proof"] == "We recently filled 2 Data Engineer roles." and r["basis"]["postings"] == 1


# --- facts
def test_facts_for_a_long_open_role():
    f = facts({"contact": {"full_name": "Asha Rao", "title": "CTO"},
               "company": {"name": "Acme AI", "industry": "software", "city": "Pune"},
               "role": "Data Engineer", "posted_at": "2026-04-03", "on_employer_board": True,
               "proof": "We recently filled 2 Data Engineer roles.", "now": NOW})
    assert f["recipient_first_name"] == "Asha" and f["their_open_roles"] == ["Data Engineer"]
    assert f["role_posted_on"] == "April 3" and f["role_open_days"] == 237
    assert f["role_listed_on"] == "Acme AI's careers page"
    assert f["our_focus"] == "software, AI and data engineering"
    assert f["placement_proof"].startswith("We recently") and f["offer_size"] == 3
    assert f["sender_name"] == "Nikita Agrawal" and "proof_basis" not in f


def test_facts_for_a_fresh_role_omit_age_and_empty_fields():
    f = facts({"contact": {"full_name": "Asha", "title": None}, "company": {"name": "Acme"}, "role": "Data Engineer",
               "posted_at": "2026-11-20", "on_employer_board": False, "proof": None, "now": NOW})
    assert not {"role_open_days", "role_posted_on", "role_listed_on", "placement_proof", "company_city",
                "recipient_title"} & set(f)
