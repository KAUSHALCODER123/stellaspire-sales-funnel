import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(autouse=True)
def config_dir(tmp_path, monkeypatch):
    """Each test gets its own copy of config/ with warm-up started on 2026-11-02 (a Monday)."""
    dest = tmp_path / "config"
    shutil.copytree(ROOT / "config", dest)
    settings = json.loads((dest / "settings.json").read_text())
    settings["warmup_start_date"] = "2026-11-02"
    (dest / "settings.json").write_text(json.dumps(settings))
    monkeypatch.setenv("SS_CONFIG_DIR", str(dest))
    return dest


@pytest.fixture(autouse=True)
def state_dir(tmp_path, monkeypatch):
    path = tmp_path / "state"
    monkeypatch.setenv("SS_STATE_DIR", str(path))
    return path


@pytest.fixture
def set_settings(config_dir):
    def apply(**changes):
        path = config_dir / "settings.json"
        data = json.loads(path.read_text())
        path.write_text(json.dumps({**data, **changes}))
    return apply


@pytest.fixture
def add_rows(config_dir):
    def add(name, *lines):
        with (config_dir / name).open("a", encoding="utf-8") as fh:
            fh.write("".join(line + "\n" for line in lines))
    return add
