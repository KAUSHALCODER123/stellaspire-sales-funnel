import json

from sslib.compose import compose
from sslib.email_check import check_email

from test_email_check import ASK, FACTS, FOLLOW, INTRO, SUBJECT, email1

OPT_OUT = 'If this isn\'t relevant, reply "no" and I won\'t write again.'
PROOF = "We recently filled 2 Data Engineer roles."


def test_email_one_inserts_the_proof_between_intro_and_ask_and_ends_with_the_signature():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": PROOF}})
    assert r["subject"] == SUBJECT
    assert OPT_OUT not in r["body"] and OPT_OUT not in r["body_html"]
    body = r["body"]
    assert body.index(INTRO) < body.index(PROOF) < body.index(ASK)
    assert body.count(PROOF) == 1
    assert body.endswith(
        "Nikita\nFounder, Stellaspire\n+91 7024766117 | stellaspire.com | linkedin.com/company/stellaspire")


def test_email_one_without_proof_has_no_gap():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": FACTS})
    assert "\n\n\n" not in r["body"] and OPT_OUT not in r["body"]


def test_proof_is_dropped_when_it_leaves_the_model_too_little_room():
    long_proof = " ".join(["word"] * 60) + "."
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": long_proof}})
    assert long_proof not in r["body"] and "error" not in r


def test_follow_up_gets_signature_and_no_subject():
    r = compose({"step": 2, "body": FOLLOW, "facts": FACTS})
    assert "subject" not in r and r["body"].startswith("Hi Asha,") and OPT_OUT not in r["body"]


def test_failing_text_returns_an_error_with_hints_and_no_body():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(INTRO + " We placed 12 people."), "facts": FACTS})
    assert r["error"] == "email_failed_checks" and r["problems"] and r["hints"] and "body" not in r


def test_bad_subject_blocks_step_one():
    assert compose({"step": 1, "subject": "Applications Wanted", "body": email1(), "facts": FACTS})["error"]


def test_composed_text_without_signature_passes_check_email():
    r = compose({"step": 1, "subject": SUBJECT, "body": email1(), "facts": {**FACTS, "placement_proof": PROOF}})
    unsigned = r["body"].split("\nFounder, Stellaspire")[0]
    assert check_email({"step": 1, "subject": SUBJECT, "body": unsigned, "facts": {**FACTS, "placement_proof": PROOF}})["ok"]
    assert json.dumps(r)  # serialisable


def _compose_one(step=2):
    return compose({"step": step, "body": FOLLOW if step == 2 else INTRO, "facts": FACTS})


def test_html_body_has_the_live_signature_with_logo_links_and_title_under_the_name():
    out = _compose_one()
    page = out["body_html"]
    assert "<br>Founder, Stellaspire<br><br>" in page                      # title sits directly under the sign-off name
    assert '<img src="https://cdn.prod.website-files.com/' in page and 'height="56"' in page
    assert '+91 7024766117 | <a href="https://stellaspire.com">stellaspire.com</a> | ' \
           '<a href="https://www.linkedin.com/company/stellaspire/">LinkedIn</a>' in page
    assert "write again" not in page and page.endswith("</a>")


def test_html_body_escapes_the_email_text_and_keeps_line_breaks():
    out = compose({"step": 2, "body": FOLLOW.replace("Nikita", "Nikita"), "facts": FACTS})
    assert "<script" not in out["body_html"] and "\n" not in out["body_html"].split("<br>Founder")[0]
    assert "<br><br>" in out["body_html"]


def test_plain_body_shows_short_website_and_linkedin_labels():
    assert "+91 7024766117 | stellaspire.com | linkedin.com/company/stellaspire" in _compose_one()["body"]


def test_opt_out_line_is_added_only_when_configured():
    from sslib.compose import signature
    cfg = {"sender_title": "Founder", "sender_company": "Stellaspire"}
    assert signature(cfg) == "Founder, Stellaspire"
    assert signature({**cfg, "opt_out_line": OPT_OUT}).endswith("\n\n" + OPT_OUT)
