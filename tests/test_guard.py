from sslib.guard import check_contacts

NOW = "2026-11-26T10:00:00+05:30"


def cand(email="asha@acme.in", domain="acme.in", **over):
    base = {"email": email, "email_status": "verified", "title": "CTO", "country": "India",
            "company": {"name": "Acme", "domain": domain}, "segment": "tech_ai_data"}
    return {**base, **over}


def run(*cands, history=None, **extra):
    r = check_contacts({"candidates": list(cands), "history": history or {}, "now": NOW, **extra})
    return r["results"]


def reasons(*cands, **kw):
    return [r["reasons"] for r in run(*cands, **kw)]


def test_clean_candidate_is_allowed():
    assert run(cand()) == [{"email": "asha@acme.in", "allowed": True, "reasons": []}]


def test_unverified_off_domain_and_role_mailbox():
    assert reasons(cand(email_status="guessed")) == [["email_not_verified"]]
    assert reasons(cand(email="asha@gmail.com")) == [["email_off_company_domain"]]
    assert reasons(cand(email="hr@acme.in")) == [["role_mailbox"]]


def test_subdomain_of_company_domain_is_on_domain():
    assert reasons(cand(email="asha@mail.acme.in")) == [[]]


def test_country_and_title():
    assert reasons(cand(country="United States")) == [["country_not_allowed"]]
    assert reasons(cand(title="Intern")) == [["title_not_buyer"]]
    assert reasons(cand(segment="bfsi", title="CTO")) == [["title_not_buyer"]]


def test_same_address_via_two_companies_is_blocked_the_second_time():
    a = cand()
    b = cand(domain="acme.in", segment="growth", title="CEO")  # same address again under another segment
    b["company"] = {"name": "Acme Growth", "domain": "acme.in"}
    assert reasons(a, b)[1] == ["contact_in_cooldown"]


def test_same_address_cannot_pass_in_one_batch_even_for_other_company_names():
    first = cand("asha@acme.in")
    second = cand("asha@acme.in", domain="acme.in")
    second["company"]["name"] = "Other"
    results = run(first, second)
    assert [r["allowed"] for r in results] == [True, False]
    assert "contact_in_cooldown" in results[1]["reasons"]


def test_address_sent_within_90_days_is_in_cooldown_but_not_after():
    recent = {"sent_to": [{"email": "asha@acme.in", "at": "2026-09-10T10:00:00+05:30"}]}  # 77 days
    old = {"sent_to": [{"email": "asha@acme.in", "at": "2026-08-01T10:00:00+05:30"}]}  # 117 days
    assert reasons(cand(), history=recent) == [["contact_in_cooldown"]]
    assert reasons(cand(), history=old) == [[]]


def test_one_open_sequence_per_company():
    h = {"open_threads_by_domain": {"acme.in": ["ravi@acme.in"]}}
    assert reasons(cand(), history=h) == [["company_has_active_sequence"]]


def test_second_contact_in_the_same_batch_is_blocked_by_the_open_sequence_rule():
    assert reasons(cand("a@acme.in"), cand("b@acme.in")) == [[], ["company_has_active_sequence"]]


def test_max_two_contacts_per_company_across_history():
    h = {"sent_to": [{"email": "x@acme.in", "at": "2026-10-01T10:00:00+05:30"},
                     {"email": "y@acme.in", "at": "2026-10-05T10:00:00+05:30"}]}
    assert reasons(cand("z@acme.in"), history=h) == [["company_contact_limit"]]
    assert reasons(cand("z@acme.in"), history={"sent_to": h["sent_to"][:1]}) == [[]]


def test_do_not_contact_csv_by_address_and_domain(add_rows):
    add_rows("do-not-contact.csv", "asha@acme.in,unsubscribed,2026-11-01", "blocked.com,asked,2026-11-01")
    assert reasons(cand()) == [["suppressed"]]
    assert reasons(cand("bob@acme.in")) == [[]]
    assert reasons(cand("bob@sub.blocked.com", domain="sub.blocked.com")) == [["suppressed"]]


def test_do_not_contact_input_is_treated_like_the_csv():
    assert reasons(cand(), do_not_contact=["ASHA@acme.in"]) == [["suppressed"]]
    assert reasons(cand("bob@mail.acme.in"), do_not_contact=["acme.in"]) == [["suppressed"]]
    assert reasons(cand("bob@acme.in"), do_not_contact=["other.in"]) == [[]]
    assert reasons(cand("bob@notacme.in", domain="notacme.in"), do_not_contact=["acme.in"]) == [[]]


def test_seed_list_blocks_address_and_whole_company_domain(add_rows):
    add_rows("already-contacted.csv", "ravi@acme.in,,2026-06-01,engine", ",oldco.com,2026-05-01,engine")
    assert reasons(cand("ravi@acme.in")) == [["already_contacted"]]
    assert reasons(cand("bob@acme.in")) == [[]]
    assert reasons(cand("x@oldco.com", domain="oldco.com")) == [["already_contacted"]]


def test_excluded_domains_setting(set_settings):
    set_settings(exclude_domains=["acme.in"])
    assert reasons(cand()) == [["domain_excluded"]]


def test_missing_history_keys_are_fine():
    assert check_contacts({"candidates": [cand()], "now": NOW})["results"][0]["allowed"]


def test_company_already_engaged_blocks_every_contact_there():
    h = {"engaged_domains": ["acme.in"]}
    assert reasons(cand("new@acme.in"), history=h) == [["company_already_engaged"]]
    assert reasons(cand("new@other.in", domain="other.in"), history=h) == [[]]
