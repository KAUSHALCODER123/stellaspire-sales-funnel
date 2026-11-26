"""Read-only access to the plugin's config/ files. Scripts never write here: the plugin dir does not persist.

settings() is config/settings.json with the chat-managed overrides merged over it, when a run has loaded them
(`ss.py load-settings` writes settings-override.json in the state dir).
"""
import csv
import json
import os
import tempfile
from pathlib import Path


def config_dir() -> Path:
    return Path(os.environ.get("SS_CONFIG_DIR") or Path(__file__).resolve().parents[2] / "config")


def state_dir() -> Path:
    return Path(os.environ.get("SS_STATE_DIR") or Path(tempfile.gettempdir()) / "stellaspire-outreach")


def override_path() -> Path:
    return state_dir() / "settings-override.json"


def base_settings() -> dict:
    return json.loads((config_dir() / "settings.json").read_text(encoding="utf-8"))


def settings() -> dict:
    cfg = base_settings()
    path = override_path()
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    return cfg


def rows(name: str) -> list[dict]:
    path = config_dir() / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
