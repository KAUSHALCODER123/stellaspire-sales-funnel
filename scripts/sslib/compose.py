"""Final email text: insert the proof into email 1 (as drafting.write_sequence does), re-check, add the signature (plain and HTML) + opt-out."""
import html
import re

from .config import settings
from .email_check import _PROOF_KEYS, _split_intro, hints_for, problems_for, reserved_words


def _site(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").rstrip("/")


def signature(cfg: dict) -> str:
    """Plain-text signature: title line, then phone | website | LinkedIn, then the opt-out line."""
    links = " | ".join(x for x in (cfg.get("sender_phone"), _site(cfg.get("sender_website")),
                                   _site(cfg.get("sender_linkedin"))) if x)
    title = ", ".join(x for x in (cfg.get("sender_title"), cfg.get("sender_company")) if x)
    return "\n".join(x for x in (title, links) if x) + f"\n\n{cfg['opt_out_line']}"


def signature_html(cfg: dict) -> str:
    """The signature the live engine sends (drafting.signature_html): title under the name, logo, phone | website | LinkedIn."""
    esc = lambda value: html.escape(value, quote=True)
    link = lambda url, label: f'<a href="{esc(url)}">{esc(label)}</a>'
    parts = [esc(cfg["sender_phone"])] if cfg.get("sender_phone") else []
    if cfg.get("sender_website"):
        parts.append(link(cfg["sender_website"], _site(cfg["sender_website"])))
    if cfg.get("sender_linkedin"):
        parts.append(link(cfg["sender_linkedin"], "LinkedIn"))
    logo = (f'<img src="{esc(cfg["sender_logo_url"])}" alt="{esc(cfg["sender_company"])}" height="56" '
            f'style="height:56px;border:0"><br>' if cfg.get("sender_logo_url") else "")
    title = f'<br>{esc(cfg["sender_title"])}, {esc(cfg["sender_company"])}' if cfg.get("sender_title") else ""
    company = "" if title else f'<b>{esc(cfg["sender_company"])}</b><br>'
    opt_out = f'<br><br><span style="color:#777;font-size:12px">{esc(cfg["opt_out_line"])}</span>'
    return f'{title}<br><br>{logo}{company}{" | ".join(parts)}{opt_out}'


def to_html(body: str, cfg: dict) -> str:
    """The email as HTML: the text escaped with line breaks kept, then the signature block."""
    return html.escape(body, quote=False).replace("\n", "<br>") + signature_html(cfg)


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
    out = {"body": f"{body}\n{signature(cfg)}", "body_html": to_html(body, cfg)}
    return {"subject": subject, **out} if step == 1 else out
