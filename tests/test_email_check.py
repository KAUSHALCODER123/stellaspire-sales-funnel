import pytest

from sslib.email_check import MAX_WORDS, check_email

ROLE = "Data Engineer"
FACTS = {"recipient_first_name": "Asha", "their_open_roles": [ROLE], "company": "Acme AI",
         "company_industry": "software", "company_city": "Bengaluru", "offer_size": 3}
INTRO = ("Saw you're hiring a Data Engineer in Bengaluru. We look for people who have run real data pipes. "
         "We find and check candidates for roles like this.")
ASK = "Want me to send 3 pre-screened data engineers for Acme AI?"
SUBJECT = "still hunting for a Data Engineer?"
FOLLOW = ("Hi Asha,\n\nFor your Data Engineer role we check what a CV hides. We ask who ran the pipes alone. "
          "We ask who fixed one at night.\n\nWorth a look?\n\nNikita")


def email1(intro=INTRO, ask=ASK):
    return f"Hi Asha,\n\n{intro}\n\n{ask}\n\nNikita"


def check(step=1, body=None, subject=SUBJECT, facts=FACTS, previous=()):
    body = email1() if body is None and step == 1 else FOLLOW if body is None else body
    return check_email({"step": step, "subject": subject, "body": body, "facts": facts, "previous": list(previous)})


def test_known_good_email_one_passes():
    r = check()
    assert r == {"ok": True, "problems": [], "hints": []}


def test_known_good_follow_up_passes_for_steps_two_to_five():
    for step in (2, 3, 4, 5):
        assert check(step, subject=None)["ok"], step


@pytest.mark.parametrize("intro", [
    "Saw you're hiring a Data Engineer. We've placed 12 people in roles like this.",  # invented figure and claim
    "Saw you're hiring a Data Engineer. We have placed five engineers recently.",
    "Saw you're hiring a Data Engineer. Our track record in this area is strong.",
    "Saw you're hiring a Data Engineer. Three pre-screened candidates are ready.",
    "Saw you're hiring a Data Engineer. Worth a look?",
    "Saw you're hiring a Data Engineer. Happy to send a shortlist of profiles.",
    "Saw you're hiring a Data Engineer. Let me know if you want to talk.",
    "Saw you're hiring a Data Engineer. Can we get on a quick call?",
    "Your hiring is slow. Saw you need a Data Engineer.",  # first sentence does not name the role
])
def test_model_intro_cannot_supply_claims_asks_or_quantities(intro):
    assert not check(body=email1(intro))["ok"]


def test_number_not_in_facts_is_rejected():
    r = check(body=email1(INTRO + " We checked 40 of them."))
    assert "email1_invented_number" in r["problems"]
    assert any("invented_number" in h for h in r["hints"])


@pytest.mark.parametrize("text", ["We placed 10-15 web developers.", "We placed 10 to 15 developers.", "about 14 developers",
                                  "over 20 hires", "20+ hires", "between 5 and 8 hires", "up to 9"])
def test_numeric_ranges_and_estimates_are_rejected(text):
    assert not check(body=email1(INTRO + " " + text))["ok"]


def test_range_gives_number_not_exact_code():
    assert "email1_number_not_exact" in check(body=email1(INTRO + " Run by 20-30 teams."))["problems"]


def test_two_question_marks_are_rejected():
    r = check(body=email1(INTRO + " Is it urgent?"))
    assert not r["ok"] and "email1_more_than_one_ask" in r["problems"]


def test_missing_closing_question_is_rejected():
    r = check(body=email1(ask="Want me to send 3 pre-screened data engineers for Acme AI."))
    assert "email1_needs_one_closing_question" in r["problems"]


@pytest.mark.parametrize("ask, code", [
    ("Want me to send 3 pre-screened candidates for this role this week?", "email1_ask_is_stock"),
    ("Want me to send some profiles?", "email1_ask_not_tailored"),
])
def test_closing_question_checks_have_distinct_codes(ask, code):
    assert code in check(body=email1(ask=ask))["problems"]


@pytest.mark.parametrize("phrase", ["with no commitment", "with no obligation", "risk-free", "at no cost to you"])
def test_qualifiers_are_rejected(phrase):
    assert not check(body=email1(ask=f"Want me to send 3 pre-screened data engineers for Acme AI {phrase}?"))["ok"]


@pytest.mark.parametrize("ask", ["Can we hop on a call about 3 data engineers for Acme AI?",
                                 "Want me to book 3 data engineers for Acme AI?"])
def test_call_requests_in_the_closing_question_are_rejected(ask):
    assert any(code in check(body=email1(ask=ask))["problems"] for code in ("email1_asks_for_call", "email1_ask_requests_call"))


def test_missing_signoff_is_rejected():
    r = check(body="Hi Asha,\n\n" + INTRO + "\n\n" + ASK)
    assert "email1_must_end_with_signoff" in r["problems"]


def test_hint_for_not_naming_the_role():
    r = check(body=email1("Your hiring is slow. Saw you need a Data Engineer."))
    assert any("exact_role" in h for h in r["hints"])


def test_email_one_is_at_most_80_words():
    r = check(body=email1(INTRO + " " + " ".join(["pipes"] * 70)))
    assert "email1_too_long" in r["problems"] and MAX_WORDS[0] == 80


def test_proof_reserves_words_in_the_model_text():
    facts = {**FACTS, "placement_proof": "We recently filled 2 Data Engineer roles."}  # 8 words
    base = len(email1().split())
    pad = "Pipes break. " * ((80 - 8 - base + 1) // 2 + 1)
    assert "email1_too_long" in check(body=email1(INTRO + " " + pad), facts=facts)["problems"]
    assert "email1_too_long" not in check(body=email1(INTRO + " " + pad), facts=FACTS)["problems"]


def test_finished_email_one_must_carry_the_proof_exactly_once_and_is_judged_at_full_length():
    proof = "We recently filled 2 Data Engineer roles."
    facts = {**FACTS, "placement_proof": proof}
    final = f"Hi Asha,\n\n{INTRO}\n\n{proof}\n\n{ASK}\n\nNikita"
    assert check(body=final, facts=facts)["ok"]
    twice = final.replace("\n\nNikita", f"\n\n{proof}\n\nNikita")
    assert "email1_proof_not_exactly_once" in check(body=twice, facts=facts)["problems"]


@pytest.mark.parametrize("subject, code", [
    ("customer success manager hiring", "subject_reads_like_an_application"),
    ("application for SDR role", "subject_reads_like_an_application"),
    ("Still Hunting For A Data Engineer", "bad_subject"),
    ("still no Data Engineer? ask us", "bad_subject"),
    ("asha, still no Data Engineer?", "bad_subject"),
    ("role", "bad_subject"),
    (None, "bad_subject"),
])
def test_bad_subjects_fail_on_step_one(subject, code):
    assert code in check(subject=subject)["problems"]


@pytest.mark.parametrize("subject", ["still hunting for a Data Engineer?", "Data Engineer seat empty since April",
                                     "the role that won't close"])
def test_role_centred_subjects_pass(subject):
    assert "bad_subject" not in check(subject=subject)["problems"]


def test_subject_is_ignored_after_step_one():
    assert check(2, subject="Still Hunting For Applications")["ok"]


@pytest.mark.parametrize("phrase", ["leverage our network", "a robust, scalable setup", "streamline hiring", "top-tier talent"])
def test_jargon_and_stock_phrases_are_rejected_in_follow_ups(phrase):
    body = FOLLOW.replace("We ask who fixed one at night.", f"We use {phrase} for your Data Engineer role.")
    assert not check(2, body=body, subject=None)["ok"]


@pytest.mark.parametrize("phrase", ["Hope this finds you well.", "Congrats on the funding.", "I came across your profile.",
                                    "An open seat slows down your team and costs you time.", "If things change, just say the word."])
def test_pleasantries_and_cliches_are_rejected_in_follow_ups(phrase):
    assert not check(3, body=FOLLOW.replace("We ask who fixed one at night.", phrase), subject=None)["ok"]


@pytest.mark.parametrize("line, code", [
    ("Hi Asha,\n\nWe can send three candidates for your Data Engineer role this week.\n\nNikita", "email2_unsupported_claim"),
    ("Hi Asha,\n\nOur 20 years of search work helps your Data Engineer role.\n\nNikita", "email2_invented_number"),
    ("Hi Asha,\n\nWe've placed engineers like this before. Data Engineer role. Want a shortlist?\n\nNikita", "email2_unsupported_claim"),
    ("Hi Asha,\n\nTwo could start in 30 days. Data Engineer role.\n\nNikita", "email2_claims_candidates_ready"),
])
def test_follow_ups_get_the_same_claim_guards(line, code):
    assert code in check(2, body=line, subject=None)["problems"]


def test_follow_ups_two_to_four_must_be_about_the_role_but_five_need_not():
    body = "Hi Asha,\n\nGood engineers are being poached right now. Worth a look?\n\nNikita"
    assert "email2_not_about_the_role" in check(2, body=body, subject=None)["problems"]
    assert "email5_not_about_the_role" not in check(5, body=body, subject=None)["problems"]
    assert "email4_not_about_the_role" not in check(4, body=body.replace("Good engineers", "This role needs engineers who"), subject=None)["problems"]


def test_follow_up_with_two_asks_and_call_requests_is_rejected():
    two = FOLLOW.replace("We ask who fixed one at night.", "Want them?")
    assert "email2_more_than_one_ask" in check(2, body=two, subject=None)["problems"]
    call = FOLLOW.replace("Worth a look?", "Can we hop on a call?")
    assert "email2_asks_for_call" in check(2, body=call, subject=None)["problems"]
    sales = FOLLOW.replace("We ask who fixed one at night.", "We ask who books their own meetings.")
    assert "email2_asks_for_call" not in check(2, body=sales, subject=None)["problems"]


def test_hard_to_read_prose_is_rejected():
    hard = ("Hi Asha,\n\nYour Data Engineer role demands comprehensive evaluation of architectural competencies "
            "alongside demonstrated organizational responsibilities throughout multidisciplinary environments.\n\nNikita")
    assert "email2_hard_to_read" in check(2, body=hard, subject=None)["problems"]


def test_links_and_template_syntax_are_rejected():
    assert "email2_has_link" in check(2, body=FOLLOW.replace("We ask who", "See acme.com. We ask who"), subject=None)["problems"]
    assert "email2_has_template_syntax" in check(2, body=FOLLOW + " {name}", subject=None)["problems"]


def test_follow_up_repeating_an_earlier_email_is_rejected():
    r = check(3, body=FOLLOW, subject=None, previous=[FOLLOW.replace("Worth a look?", "Want them?")])
    assert "email3_repeats_email1" in r["problems"]
    different = ("Hi Asha,\n\nThe good ones for a Data Engineer role are not applying. Someone is poaching them. "
                 "We go to them first.\n\nWant them?\n\nNikita")
    assert check(3, body=different, subject=None, previous=[FOLLOW])["ok"]


def test_bad_step_is_an_input_error():
    with pytest.raises(ValueError):
        check(6)
