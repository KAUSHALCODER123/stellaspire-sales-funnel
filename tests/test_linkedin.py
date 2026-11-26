from sslib.email_check import check_linkedin

FACTS = {"recipient_first_name": "Asha", "company": "Acme", "their_open_roles": ["SDR"], "offer_size": 3}


def problems(note):
    return check_linkedin({"note": note, "facts": FACTS})["problems"]


def test_good_note_passes():
    assert problems("Hi Asha, saw the SDR role at Acme. I place SDRs in Bengaluru and screen for real call volume. "
                    "Happy to connect.") == []


def test_note_over_300_chars_and_off_role_fail():
    assert "linkedin_too_long" in problems("Hi Asha, " + "word " * 70)
    assert "linkedin_not_about_the_role" in problems("Hi Asha, happy to connect.")


def test_note_rules_match_email_rules():
    assert "linkedin_invented_number" in problems("Hi Asha, we filled 12 SDR roles.")
    assert "linkedin_asks_for_call" in problems("Hi Asha, can we hop on a quick call about the SDR role?")
    assert "linkedin_has_link" in problems("Hi Asha, SDR role: see stellaspire.com")
