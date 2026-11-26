"""Final email text: insert the proof into email 1 (as drafting.write_sequence does), re-check, add signature + opt-out."""
from .config import settings
from .email_check import _PROOF_KEYS, _split_intro, hints_for, problems_for, reserved_words


def signature(cfg: dict) -> str:
    links = " | ".join(x for x in (cfg.get("sender_phone"), cfg.get("sender_website"), cfg.get("sender_linkedin")) if x)
    title = ", ".join(x for x in (cfg.get("sender_title"), cfg.get("sender_company")) if x)
    return "\n".join(x for x in (title, links) if x) + f"\n\n{cfg['opt_out_line']}"


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
    out = {"body": f"{body}\n{signature(cfg)}"}
    return {"subject": subject, **out} if step == 1 else out
