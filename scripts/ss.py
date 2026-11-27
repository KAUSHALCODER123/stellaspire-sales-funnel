#!/usr/bin/env python3
"""Stellaspire outreach decision CLI: one JSON object on stdin, one JSON object on stdout.

Bad input exits 2 with {"error": ...}. Every decision lives in sslib; this file only dispatches.
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "vendor"))  # bundled holidays, dateutil, six: used only if not installed

from sslib.apollo import ApolloError, apollo
from sslib.calendar_ist import next_step, today
from sslib.campaigns import campaign, campaign_check
from sslib.compose import compose
from sslib.email_check import check_email, check_linkedin
from sslib.fit import fit
from sslib.guard import check_contacts
from sslib.health import health
from sslib.imported import imported_leads
from sslib.hiresome import HiresomeError, hiresome
from sslib.proof import facts, proof
from sslib.roles import role_check
from sslib.sync import sync_plan
from sslib.settings_override import load_settings, settings_check

COMMANDS = {"today": today, "role-check": role_check, "check-contacts": check_contacts, "fit": fit, "proof": proof,
            "facts": facts, "check-email": check_email, "check-linkedin": check_linkedin, "compose": compose, "next-step": next_step,
            "health": health, "apollo": apollo, "hiresome": hiresome, "campaign": campaign, "imported-leads": imported_leads, "sync-plan": sync_plan,
            "campaign-check": campaign_check, "settings-check": settings_check, "load-settings": load_settings}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        print(json.dumps({"error": f"usage: ss.py <{'|'.join(COMMANDS)}>"}))
        return 2
    try:
        inp = json.load(sys.stdin)
        if not isinstance(inp, dict):
            raise ValueError("stdin must be one JSON object")
        out = COMMANDS[argv[1]](inp)
    except (ApolloError, HiresomeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except (ValueError, KeyError, TypeError) as exc:  # includes JSONDecodeError and missing keys
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
