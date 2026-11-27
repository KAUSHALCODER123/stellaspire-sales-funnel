"""The scripts must work in an environment with nothing installed (python -S ignores site-packages)."""
import json
import os
import subprocess
import sys
from pathlib import Path

SS = Path(__file__).resolve().parents[1] / "scripts" / "ss.py"


def today(now: str) -> dict:
    out = subprocess.run([sys.executable, "-S", str(SS), "today"], text=True, capture_output=True, env=dict(os.environ),
                         input=json.dumps({"sent_today": 0, "drafted_today": 0, "followups_due": 0, "now": now}))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_bundled_holidays_decide_the_day_with_nothing_installed():
    assert today("2026-11-30T07:10:00+05:30")["send_day"] is True
    assert today("2027-01-26T07:10:00+05:30")["reason"] == "public_holiday"  # Republic Day, a Tuesday
    assert today("2026-12-05T07:10:00+05:30")["reason"] == "weekend"
