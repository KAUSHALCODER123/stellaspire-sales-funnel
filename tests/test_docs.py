"""The instructions must run from a repository checkout and only call scripts that exist."""
import re
from pathlib import Path

import ss

ROOT = Path(__file__).resolve().parents[1]
DOCS = [*ROOT.glob("commands/*.md"), *ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("agents/*.md")]


def test_no_instruction_depends_on_an_installed_plugin_path():
    assert [str(f) for f in DOCS if "CLAUDE_PLUGIN_ROOT" in f.read_text(encoding="utf-8")] == []


def test_every_script_call_names_a_real_command():
    used = {m for f in DOCS for m in re.findall(r"scripts/ss\.py (?:\"?)([a-z-]+)", f.read_text(encoding="utf-8"))}
    assert used and used <= set(ss.COMMANDS), used - set(ss.COMMANDS)


def test_every_command_has_a_project_level_wrapper_pointing_at_it():
    for f in (ROOT / "commands").glob("*.md"):
        wrapper = (ROOT / ".claude" / "commands" / f"ss-{f.name}").read_text(encoding="utf-8")
        assert f"commands/{f.stem}.md" in wrapper and "$ARGUMENTS" in wrapper
