import json

import pytest

from sslib.imported import imported_leads

NOW = "2026-11-27T09:00:00+05:30"


def lead(email, posted, board=False, title="Backend Engineer"):
    return {"company": {"name": email, "domain": email.split("@")[1], "city": "Pune", "industry": "SaaS"}, "segment": "tech_ai_data",
            "contact": {"full_name": "Asha Rao", "title": "CTO", "email": email, "email_status": "verified",
                        "country": "India", "linkedin_url": "https://www.linkedin.com/in/x"},
            "role": {"title": title, "url": "https://x/job", "posted_at": posted, "on_employer_board": board}}


@pytest.fixture
def write(config_dir):
    def apply(*leads):
        (config_dir / "imported-leads.json").write_text(json.dumps({"leads": list(leads)}))
    return apply


def test_board_roles_first_then_newest_and_stale_roles_are_dropped(write):
    write(lead("a@a.in", "2026-11-20T00:00:00+05:30"),            # 7 days, apollo only
          lead("b@b.in", "2026-11-26T00:00:00+05:30"),            # 1 day, apollo only
          lead("c@c.in", "2026-11-05T00:00:00+05:30", board=True),  # 22 days: fine on a board (30-day limit)
          lead("d@d.in", "2026-11-05T00:00:00+05:30"),            # 22 days, apollo only: over the 14-day limit
          lead("e@e.in", None))
    out = imported_leads({"limit": 10, "now": NOW})
    assert [c["contact"]["email"] for c in out["candidates"]] == ["c@c.in", "b@b.in", "a@a.in"]
    assert out["skipped"] == [{"email": "d@d.in", "reason": "stale"}, {"email": "e@e.in", "reason": "undated"}]
    assert (out["fresh_total"], out["total"]) == (3, 5)


def test_limit_and_missing_file(write, config_dir):
    write(*[lead(f"x{i}@x{i}.in", "2026-11-25T00:00:00+05:30") for i in range(6)])
    assert len(imported_leads({"limit": 4, "now": NOW})["candidates"]) == 4
    (config_dir / "imported-leads.json").unlink()
    assert imported_leads({"now": NOW}) == {"candidates": [], "skipped": [], "fresh_total": 0, "total": 0}


def test_a_role_that_is_not_hireable_is_skipped(write):
    write(lead("i@i.in", "2026-11-25T00:00:00+05:30", title="Software Intern"))
    assert imported_leads({"now": NOW})["skipped"] == [{"email": "i@i.in", "reason": "not_hireable"}]
