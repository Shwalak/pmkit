"""The committed example outputs are shown in the README, so they must match what the code prints today."""

import contextlib
import io
import json
from pathlib import Path

import pytest

from pmkit.cli import main

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = json.loads((ROOT / "examples" / "commands.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_committed_output_matches_current_behaviour(name, monkeypatch):
    monkeypatch.chdir(ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main(COMMANDS[name])
    expected = f"$ pmkit {' '.join(COMMANDS[name])}\n\n" + buf.getvalue()
    committed = (ROOT / "examples" / "outputs" / f"{name}.txt").read_text(encoding="utf-8")
    assert committed == expected, f"examples/outputs/{name}.txt is stale: run python scripts/regenerate_examples.py"
