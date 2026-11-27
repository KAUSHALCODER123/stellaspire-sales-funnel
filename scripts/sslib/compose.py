"""Final email text: insert the proof into email 1 (as drafting.write_sequence does), re-check, add the opt-out line.

There is no signature block here. Nikita's Gmail signature (logo, name, title, phone, links) is appended by the Gmail
connector when a draft is created with includeSignature, so it always matches what she set up in Gmail.
"""
import html

from .config import settings
from .email_check import _PROOF_KEYS, _split_intro, hints_for, problems_for, reserved_words


def with_opt_out(body: str, cfg: dict) -> str:
    """The opt-out line goes above the sign-off, so the Gmail signature that follows the text ends the email."""
    rest, sep, signoff = body.rpartition("\n")
    if not sep or signoff.strip() != cfg["sender_first_name"]:
        return f"{body}\n\n{cfg['opt_out_line']}"
    return f"{rest.rstrip()}\n\n{cfg['opt_out_line']}\n\n{signoff}"


def to_html(body: str) -> str:
    """The email as HTML: the text escaped, with its line breaks kept."""
    return html.escape(body, quote=False).replace("\n", "<br>")


def _fail(problems: list[str]) -> dict:
    return {"error": "email_failed_checks", "problems": problems, "hints": hints_for(problems)}


def compose(inp: dict) -> dict:
    cfg, step, facts = settings(), int(inp["step"]), inp["facts"]
    body, subject, previous = inp["body"].strip(), (inp.get("subject") or "").strip(), inp.get("previous") or []
    if step == 1:
        problems = problems_for(1, subject, body, facts, previous)  # the model's own text first
        if problems:
            return _fail(problems)
        proof = facts.get("placement_proof") if reserved_words(facts) else ""
        model_facts = {k: v for k, v in facts.items() if k not in _PROOF_KEYS}
        intro, ask, signoff = _split_intro(body, model_facts, cfg["sender_first_name"])
        body = "\n\n".join(filter(None, [intro, proof, ask, signoff]))
        problems = problems_for(1, subject, body, {**model_facts, "placement_proof": proof} if proof else model_facts,
                                previous, final=bool(proof))
    else:
        problems = problems_for(step, None, body, facts, previous)
    if problems:
        return _fail(problems)
    final = with_opt_out(body, cfg)
    out = {"body": final, "body_html": to_html(final)}
    return {"subject": subject, **out} if step == 1 else out
