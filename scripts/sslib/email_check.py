"""Per-step email lint, ported from drafting.py validate()/_split_intro(). All regexes are verbatim."""
import json
import re
from datetime import datetime
from difflib import SequenceMatcher

from .config import settings
from .proof import OFFER_SIZE

STEPS = 5
MAX_WORDS = (80, 50, 50, 50, 45)  # email 1 counts everything, including the proof the application adds
MIN_MODEL_INTRO_WORDS = 24  # below this the proof is dropped so the model keeps room for opener, problem, what we do and the ask
_MONTHS = {f"{datetime(2000, m, 1):%B}" for m in range(1, 13)}
MAX_GRADE, MAX_SENTENCE_WORDS = 7.0, 18  # reading level: plain words, short sentences
_PROOF_KEYS = ("placement_proof", "proof_basis")  # app-authored; never shown to the model
REPEAT_RATIO = 0.8  # a follow-up this close to an earlier email is a repeat

_BANNED = re.compile(
    r"[—–]|i hope|hope (?:this|you|all)|congrat|i came across|i wanted to reach out|reaching out|quick question|"
    r"here'?s the thing|i'?ll be honest|leverage|synergy|best-in-class|unlock|next level|circle back|touch base|"
    r"just checking in|following up on my|caught my eye|not about [^.?!]{1,60}, (it'?s|but)|"
    r"it'?s not [^.?!]{1,60}, it'?s|\bno \w+, no \w+|"
    r"(don'?t|doesn'?t|do not|does not|isn'?t|aren'?t) (need|just|only)? ?[^.?!;]{1,60}[;,] (you |it )?(just |only )?"
    r"(need|want|is|are)\b|exact (same )?(problem|bottleneck|challenge|situation)|"
    r"\b(?:no|without(?: any)?|zero)[\s-]+(?:commitments?|obligations?|strings attached|cost|charge|risk|pressure|catch)\b|"
    r"\b(?:commitment|obligation|risk)[\s-]*free\b|non-binding|free of charge|nothing to lose|"
    # obvious pain lines founders skip
    r"\bopen (?:seat|role|position) (?:slows|costs|hurts)|\bcosts? (?:you )?(?:time|output)|"
    r"\bslows? (?:down )?(?:your|the) team|takes? hours|away from your day|\bwrong (?:person|people|hire)|"
    r"sort(?:ing)? through|\bthe pile\b|clean list|"
    # the breakup template
    r"under control|say the word|if (?:things|anything) changes?|not the right time|close (?:your|the) file|"
    r"\bwon'?t bother you|\bi'?ll leave it there|"
    # machine-sounding phrasing
    r"help your \w+ grow|ready to work as|picked to help", re.I)

# Model text may not say candidates are ready or waiting: the sequence shows none.
_AVAILABILITY = re.compile(
    r"\bready (?:to (?:work|start|join|go|interview)|today|now|for you)\b|"
    r"\b(?:available|free) (?:now|today|immediately|to start)\b|"
    r"\b(?:could|can) start (?:in|by|on|within|this|next|today|immediately)\b|\bstart in \d+|"
    r"\balready (?:picked|chosen|selected|shortlisted|screened|lined up|found)\b|\bfound your\b|\bwaiting for you\b|"
    r"\b(?:have|got) (?:\w+ ){0,2}(?:candidates|profiles|people) (?:ready|lined up|waiting)\b", re.I)
# A subject about a candidate rather than their role ("customer success manager hiring") reads like a job application.
_CANDIDATE_SUBJECT = re.compile(
    r"\bhiring\b|\bapplica\w*|\bapply\w*|\bcandidates?\b|\bjobs?\b|\bresume\b|\bcv\b|\bvacanc\w*|"
    r"\bopening\b|\bposition\b|\binterested in\b", re.I)

_JARGON = re.compile(
    r"\b(?:streamlin\w*|top[- ]tier|end[- ]to[- ]end|cutting[- ]edge|world[- ]class|state[- ]of[- ]the[- ]art|"
    r"game[- ]chang\w*|robust|holistic|scalable|seamless\w*|innovative|ecosystem|bandwidth|paradigm|value[- ]add|"
    r"utili[sz]\w*|optimi[sz]\w*|mission[- ]critical|turnkey|stakeholders?|talent (?:pipeline|acquisition|strategy)|"
    r"solutions?|empower\w*|revolutioni[sz]\w*|disrupt\w*|deliverables?|synerg\w*|talent partner\w*|"
    r"high[- ]caliber|best[- ]fit|passive candidates?)\b", re.I)

# Exact numbers only: no ranges, no estimates.
_RANGE = re.compile(
    r"\b\d+\s*(?:-|to)\s*\d+\b|\b\d+\s*\+|\b(?:about|around|roughly|approximately|nearly|almost|over|under|"
    r"more than|up to|between)\s+\d+|\b\d+\s*(?:weeks?|months?|years?)\b", re.I)

# Model-written text may not state or imply placement evidence: only the app-authored proof may.
_CLAIM = re.compile(
    r"\b(?:we|i)(?:'ve| have)? (?:placed|hired|filled|helped (?:\w+ ){0,3}hire)\b|\bwe place\b|"
    r"\bour (?:placements|clients|track record|hires|customers)\b|\b(?:clients|companies) (?:like|such as)\b|"
    r"\b(?:recent|recently|past|previous) (?:placements?|hires?)\b|"
    r"\bplaced (?:\w+ ){0,3}(?:candidates|people|professionals|engineers)\b|\btrack record\b|"
    r"\bsuccessfully (?:placed|filled)\b", re.I)
_NUMBER = (r"(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
           r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|thousands?|dozens?)"
           r"(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?")
_UNIT = (r"(?:placements?|hires?|candidates?|profiles?|people|professionals|engineers?|clients?|companies|searches|"
         r"roles|years?|months?|weeks?|percent)")
# A written-out quantity of something we could claim ("three pre-screened candidates", "ten years", "one placement").
_NUMBER_CLAIM = re.compile(
    rf"\b({_NUMBER})(?:[\s-]+[\w'-]+){{0,2}}[\s-]+{_UNIT}\b|\b(one)(?:[\s-]+[\w']+)?[\s-]+(?:placements?|hires?|clients?)\b",
    re.I)
# No step asks for a call or meeting; free work (the profiles) is the only offer.
# Sales and support roles are described in these same words ("SDRs who book meetings", "a cold call"), so the
# broad pattern is judged only on ask sentences, minus any "who/that ..." clause describing the person; phrases
# that can only be a request to meet us are rejected anywhere.
_CALL_REQUEST = re.compile(r"\b(?:a|an|the|your|short|quick)\s+(?:\w+\s+)?(?:call|meeting|chat|demo)\b|"
                           r"\b(?:hop on|jump on|book|schedule|calendar)\b", re.I)
_CALL_ANYWHERE = re.compile(
    r"\b(?:hop|jump|get) on (?:a |the )?(?:\w+ )?call\b|\b(?:quick|short|brief|\d+[\s-]*min\w*)\s+(?:\w+\s+)?(?:call|chat|meeting)\b|"
    r"\bcalendar\b|\b(?:call|chat|meeting|demo|talk) with (?:me|us)\b|\b(?:free|time) (?:for|to) (?:a )?(?:call|chat|talk|meet)\b|"
    r"\b(?:schedule|set up|book|arrange|grab) (?:a|some|an) (?:\w+ )?(?:call|chat|meeting|time|slot)\b", re.I)
_ASK_SENTENCE = re.compile(r"[^.!?\n]*\?|\b(?:let'?s|let us|can we|could we|shall we|should we)\b[^.!?\n]*", re.I)
_DESCRIBES_PERSON = re.compile(r"\b(?:who|that|which|whose)\b.*", re.I)


def _asks_for_call(text: str) -> bool:
    return bool(_CALL_ANYWHERE.search(text)) or any(
        _CALL_REQUEST.search(_DESCRIBES_PERSON.sub("", m.group(0))) for m in _ASK_SENTENCE.finditer(text))
# Email 1 is greeting + signal + problem + what we do, then one closing question: an ask anywhere before it competes.
_COMPETING_ASK = re.compile(
    r"\?|\b(?:let me know|reply|get back|would you|could you|can we|shall i|should i|want me|happy to|worth a|open to)\b|"
    r"\b(?:send|share|forward|introduce|offer|put together)\b[^.]{0,40}\b(?:profiles?|shortlists?|candidates?)\b", re.I)
# The closing question must be written for the company; the old fixed line (and near copies of it) is rejected.
_STOCK_ASK = "want me to send 3 prescreened candidates for this role this week"
_GENERIC_WORDS = {"senior", "junior", "lead", "manager", "role", "roles", "head", "principal", "associate"}
_ROLE_REFERENCE = re.compile(r"\b(?:this|that|the|your) (?:open )?(?:\w+ )?role\b", re.I)


def _grade(text: str) -> tuple[float, int]:
    """Flesch-Kincaid grade and the longest sentence, in words, of plain prose."""
    sentences = [s.split() for s in re.split(r"[.!?]+", text) if s.split()]
    words = [w for s in sentences for w in s]
    if not words:
        return 0.0, 0
    syllables = sum(max(1, len(re.findall(r"[aeiouy]+", re.sub(r"e$", "", w.lower())))) for w in words)
    return 0.39 * len(words) / len(sentences) + 11.8 * syllables / len(words) - 15.59, max(len(s) for s in sentences)


def _too_hard_to_read(body: str, names: list[str]) -> bool:
    """Reading level of the model's own prose: greeting, sign-off, role and company names are not scored."""
    lines = [line for line in body.splitlines() if len(line.split()) > 2]
    text = " ".join(lines)
    for name in names:
        text = re.sub(re.escape(name), "x", text, flags=re.I)
    grade, longest = _grade(text)
    return len(text.split()) >= 8 and (grade > MAX_GRADE or longest > MAX_SENTENCE_WORDS)


def _unsupported_claim(own: str, facts_json: str) -> bool:
    """Placement claims, or a written-out quantity of something claimable that the facts do not contain."""
    return bool(_CLAIM.search(own)) or any((m.group(1) or m.group(2)).lower() not in facts_json.lower()
                                          for m in _NUMBER_CLAIM.finditer(own))


def _tailoring_terms(facts: dict, role: str) -> tuple[str, list[str]]:
    """The company name and the meaningful words of the role, industry and city an ask can be tailored with."""
    text = " ".join(str(facts.get(key) or "") for key in ("company_industry", "company_city")) + f" {role}"
    return (facts.get("company") or "").casefold(), sorted(
        {w for w in re.findall(r"[a-z0-9+#]+", text.casefold()) if len(w) > 3 and w not in _GENERIC_WORDS})


def _split_intro(email: str, facts: dict, first_name: str) -> tuple[str, str, str] | list[str]:
    """Model-written email 1 as (intro, closing question, sign-off), or the reasons it cannot be used."""
    role = (facts.get("their_open_roles") or [""])[0]
    body, sep, signoff = email.strip().rpartition("\n")
    if not sep or signoff.strip() != first_name:
        return ["email1_must_end_with_signoff"]
    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) < 2 or role.casefold() not in re.split(r"(?<=[.!?])\s", lines[1])[0].casefold():  # first sentence
        return ["email1_must_open_by_naming_the_exact_role"]
    intro, _, ask = body.strip().rpartition("\n")
    intro, ask = intro.strip(), ask.strip()
    problems = []
    if len(lines) < 3 or not ask.endswith("?") or email.count("?") != 1:
        problems.append("email1_needs_one_closing_question")
    # Call words alone ("reps who book demos") describe the role; only a call request competes with the ask.
    if _COMPETING_ASK.search(intro) or _asks_for_call(intro):
        problems.append("email1_has_competing_ask")
    if _asks_for_call(ask):
        problems.append("email1_ask_requests_call")
    company, terms = _tailoring_terms(facts, role)
    if not (company and company in ask.casefold()) and not any(re.search(rf"\b{re.escape(t)}", ask.casefold()) for t in terms):
        problems.append("email1_ask_not_tailored")
    if SequenceMatcher(None, re.sub(r"[^a-z0-9 ]", "", ask.casefold()), _STOCK_ASK).ratio() >= 0.85:
        problems.append("email1_ask_is_stock")
    return problems or (intro, ask, signoff.strip())


# What each rejection means, so a retry can fix it rather than guess (a contact that fails every attempt is not redrafted).
_RETRY_HINTS = {
    "hard_to_read": "hard_to_read: every sentence under 15 words, mostly one- and two-syllable words.",
    "bad_subject": "bad_subject: 2 to 7 words, lowercase except the role, an abbreviation, a month or the company, "
                   "at most one question mark and only at the end, no first name.",
    "reads_like_an_application": "subject_reads_like_an_application: write about their open role, never 'hiring', "
                                 "'job', 'application' or 'candidate'.",
    "more_than_one_ask": "more_than_one_ask: one question mark per email, in its last line.",
    "asks_for_call": "asks_for_call: never ask to meet, talk or call; the only offer is profiles or a reply.",
    "machine_sounding": "machine_sounding: drop stock phrases, obvious pain lines and dashes.",
    "claims_candidates_ready": "claims_candidates_ready: never say anyone is ready, available, picked or could start.",
    "invented_number": "invented_number: the only numbers allowed are offer_size, role_open_days and role_posted_on.",
    "number_not_exact": "number_not_exact: give time as exact days or 'since <month>', never weeks, months or years.",
    "must_open_by_naming": "email1_must_open_by_naming_the_exact_role: the first sentence after the greeting names "
                           "the exact role title from the facts.",
    "ask_not_tailored": "email1_ask_not_tailored: the closing question names the company, its industry, its city "
                        "or a word from the role.",
}


def reserved_words(facts: dict) -> int:
    """Words the app will add to email 1; zero when the proof would leave the model too little room."""
    reserved = len((facts.get("placement_proof") or "").split())
    return reserved if MAX_WORDS[0] - reserved >= MIN_MODEL_INTRO_WORDS else 0


def problems_for(step: int, subject: str | None, body: str, facts: dict, previous: list[str] = (),
                 final: bool = False) -> list[str]:
    """Problems with one email, applying the drafting.py validate() checks that belong to this step.

    final=False checks the model's own text (email 1 without the proof, its word limit reduced by the proof);
    final=True checks the finished email 1, which must carry the proof exactly once.
    """
    i, problems, body = step - 1, [], body.strip()
    model_facts = {**{k: v for k, v in facts.items() if k not in _PROOF_KEYS}, "offer_size": OFFER_SIZE}
    proof = facts.get("placement_proof") or ""
    first_name = (facts.get("recipient_first_name") or "").lower()
    role = (facts.get("their_open_roles") or [""])[0]
    facts_json = json.dumps(facts if final else model_facts)
    if i == 0:
        subject = (subject or "").strip()
        words = subject.split()
        # Lowercase apart from the role title, company name and month names, which keep their casing ("SDR", "April").
        proper = set(re.findall(r"[\w+#]+", f"{role} {facts.get('company') or ''}")) | _MONTHS
        # Short all-caps abbreviations ("CSM", "QA") are how people name roles; Title Case is what is rejected.
        shouting = [w for w in re.findall(r"[\w+#]+", subject)
                    if w != w.lower() and w not in proper and not (w.isupper() and len(w) <= 5)]
        if (not 2 <= len(words) <= 7 or shouting or re.search(r"[!:;\"]", subject) or subject.count("?") > 1
                or (subject.count("?") == 1 and not subject.endswith("?"))
                or (first_name and first_name in re.findall(r"[\w']+", subject.lower()))):
            problems.append("bad_subject")
        if _CANDIDATE_SUBJECT.search(subject):
            problems.append("subject_reads_like_an_application")
    else:
        subject = ""
    if not body:
        return problems + [f"email{step}_empty"]
    names = [n for n in (role, facts.get("company")) if n]
    allowed_numbers = set(re.findall(r"\d+", facts_json))
    text = f"{subject}\n{body}" if i == 0 else body
    # Claims are judged on what the model wrote, closing question included; only the app-authored proof is exempt.
    own_body = body.replace(proof, "") if i == 0 and final and proof else body
    own = f"{subject}\n{own_body}" if i == 0 else own_body
    limit = MAX_WORDS[i] - (reserved_words(facts) if i == 0 and not final else 0)
    if len(body.split()) > limit:
        problems.append(f"email{step}_too_long")
    if re.search(r"https?://|www\.|\S+\.(com|in|io|co)\b", text, re.I):
        problems.append(f"email{step}_has_link")
    if re.search(r"[{}]|\[[^\]]*\]|<[^>]+>", text):
        problems.append(f"email{step}_has_template_syntax")
    if _BANNED.search(text):
        problems.append(f"email{step}_machine_sounding")
    if _JARGON.search(own):
        problems.append(f"email{step}_jargon")
    if _too_hard_to_read(own_body, names):
        problems.append(f"email{step}_hard_to_read")
    if _asks_for_call(own):
        problems.append(f"email{step}_asks_for_call")
    if i < STEPS - 1 and len(re.findall(r"\?", body)) > 1:
        problems.append(f"email{step}_more_than_one_ask")
    if set(re.findall(r"\d+", text)) - allowed_numbers:
        problems.append(f"email{step}_invented_number")
    if _RANGE.search(text):
        problems.append(f"email{step}_number_not_exact")
    if _unsupported_claim(own, facts_json):
        problems.append(f"email{step}_unsupported_claim")
    if _AVAILABILITY.search(own):
        problems.append(f"email{step}_claims_candidates_ready")
    if role and 1 <= i <= 3 and role.casefold() not in body.casefold() and not _ROLE_REFERENCE.search(body):
        problems.append(f"email{step}_not_about_the_role")
    if i == 0 and final and proof and body.count(proof) != 1:
        problems.append("email1_proof_not_exactly_once")
    if i == 0 and not final and not problems:
        split = _split_intro(body, model_facts, settings()["sender_first_name"])
        if isinstance(split, list):
            problems.extend(split)
    squash = lambda t: re.sub(r"[^a-z0-9 ]", "", t.casefold())
    problems.extend(f"email{step}_repeats_email{n}" for n, earlier in enumerate(previous, start=1)
                    if i > 0 and SequenceMatcher(None, squash(body), squash(earlier)).ratio() >= REPEAT_RATIO)
    return problems


def hints_for(problems: list[str]) -> list[str]:
    return sorted({hint for code, hint in _RETRY_HINTS.items() if any(code in p for p in problems)})


def check_email(inp: dict) -> dict:
    facts, step = inp["facts"], int(inp["step"])
    if not 1 <= step <= STEPS:
        raise ValueError("step must be 1-5")
    proof = facts.get("placement_proof") or ""
    final = step == 1 and bool(proof) and proof in inp["body"]
    problems = problems_for(step, inp.get("subject"), inp["body"], facts, inp.get("previous") or [], final)
    return {"ok": not problems, "problems": problems, "hints": hints_for(problems)}


LINKEDIN_MAX_CHARS = 300  # LinkedIn's limit for a connection-request note


def check_linkedin(inp: dict) -> dict:
    """Problems with a LinkedIn connection note: the email copy rules, a 300-character limit, and the role named."""
    note, facts = (inp["note"] or "").strip(), inp["facts"]
    role = (facts.get("their_open_roles") or [""])[0]
    facts_json = json.dumps(facts)
    checks = {
        "too_long": len(note) > LINKEDIN_MAX_CHARS,
        "empty": not note,
        "has_link": bool(re.search(r"https?://|www\.|\S+\.(com|in|io|co)\b", note, re.I)),
        "has_template_syntax": bool(re.search(r"[{}]|\[[^\]]*\]|<[^>]+>", note)),
        "machine_sounding": bool(_BANNED.search(note)),
        "jargon": bool(_JARGON.search(note)),
        "asks_for_call": _asks_for_call(note),
        "more_than_one_ask": note.count("?") > 1,
        "invented_number": bool(set(re.findall(r"\d+", note)) - set(re.findall(r"\d+", facts_json))),
        "number_not_exact": bool(_RANGE.search(note)),
        "unsupported_claim": _unsupported_claim(note, facts_json),
        "claims_candidates_ready": bool(_AVAILABILITY.search(note)),
        "not_about_the_role": bool(role) and role.casefold() not in note.casefold(),
    }
    problems = [f"linkedin_{code}" for code, failed in checks.items() if failed]
    return {"ok": not problems, "problems": problems}
