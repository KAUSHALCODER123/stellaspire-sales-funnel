import json

from sslib.compose import compose
from sslib.email_check import check_email

from test_email_check import ASK, FACTS, FOLLOW, INTRO, SUBJECT, email1

OPT_OUT = 'If this isn\'t relevant, reply "no" and I won\'t write again.'
PROOF = "We recently filled 2 Data Engineer roles."
TAIL = "\n\n" + OPT_OUT + "\n\nNikita"  # opt-out above the sign-off: Gmail's signature follows the sign-off


def test_email_one_inserts_the_proof_between_intro_and_ask_and_puts_the_opt_out_above_the_sign_off():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": PROOF}})
    assert r["subject"] == SUBJECT
    body = r["body"]
    assert body.index(INTRO) < body.index(PROOF) < body.index(ASK) < body.index(OPT_OUT)
    assert body.count(PROOF) == 1
    assert body.endswith(TAIL)


def test_email_one_without_proof_has_no_gap():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": FACTS})
    assert "\n\n\n" not in r["body"] and r["body"].endswith(TAIL)


def test_proof_is_dropped_when_it_leaves_the_model_too_little_room():
    long_proof = " ".join(["word"] * 60) + "."
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": long_proof}})
    assert long_proof not in r["body"] and "error" not in r


def test_follow_up_has_no_subject_and_the_same_opt_out_placement():
    r = compose({"step": 2, "body": FOLLOW, "facts": FACTS})
    assert "subject" not in r and r["body"].startswith("Hi Asha,") and r["body"].endswith(TAIL)


def test_failing_text_returns_an_error_with_hints_and_no_body():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(INTRO + " We placed 12 people."), "facts": FACTS})
    assert r["error"] == "email_failed_checks" and r["problems"] and r["hints"] and "body" not in r


def test_bad_subject_blocks_step_one():
    assert compose({"step": 1, "subject": "Applications Wanted", "body": email1(), "facts": FACTS})["error"]


def test_composed_text_without_the_opt_out_passes_check_email():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": PROOF}})
    plain = r["body"].replace("\n\n" + OPT_OUT, "")
    assert check_email({"step": 1, "subject": SUBJECT, "body": plain, "facts": {**FACTS, "placement_proof": PROOF}})["ok"]
    assert json.dumps(r)  # serialisable


def test_no_signature_block_is_added_because_gmail_appends_the_real_one():
    out = compose({"step": 2, "body": FOLLOW, "facts": FACTS})
    for text in (out["body"], out["body_html"]):
        assert "Founder" not in text and "7024766117" not in text and "<img" not in text and "linkedin" not in text.lower()


def test_html_body_escapes_the_text_and_keeps_line_breaks():
    html = compose({"step": 2, "body": FOLLOW, "facts": FACTS})["body_html"]
    assert "<script" not in html and "\n" not in html and "<br><br>" in html
    assert "I won't write again" in html
