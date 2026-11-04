"""Regenerate examples/outputs/*.txt from examples/commands.json.

Run from the repository root:  python scripts/regenerate_examples.py
tests/test_examples_current.py fails if the committed outputs drift from the code.
"""

import contextlib
import io
import json
from pathlib import Path

from pmkit.cli import main

ROOT = Path(__file__).resolve().parent.parent


def run(argv: list[str]) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main(argv)
    return buf.getvalue()


if __name__ == "__main__":
    import os

    os.chdir(ROOT)
    commands = json.loads((ROOT / "examples" / "commands.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "examples" / "outputs"
    out_dir.mkdir(exist_ok=True)
    for name, argv in commands.items():
        (out_dir / f"{name}.txt").write_text(f"$ pmkit {' '.join(argv)}\n\n" + run(argv), encoding="utf-8")
        print("wrote", f"examples/outputs/{name}.txt")
