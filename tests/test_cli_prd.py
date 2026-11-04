import json

import pytest

from pmkit.cli import main
from pmkit.prd import FAIL, check_prd


def test_template_is_structurally_complete_but_unfinished(capsys):
    assert main(["prd", "new", "--title", "Demo"]) == 0
    template = capsys.readouterr().out
    assert template.startswith("# Demo")
    findings = check_prd(template)
    # every required section exists, so no "missing section" failures...
    assert not [f for f in findings if f.status == FAIL and f.check == "section"]
    # ...but it is flagged as unfinished: placeholders remain and the metrics have no numbers yet
    assert any(f.check == "placeholder" for f in findings)
    assert any(f.check == "metrics" and f.status == FAIL for f in findings)


def test_prd_new_writes_a_file_and_refuses_to_overwrite(tmp_path, capsys):
    target = tmp_path / "prd.md"
    assert main(["prd", "new", "--title", "Thing", "--out", str(target)]) == 0
    assert "# Thing" in target.read_text(encoding="utf-8") and "pmkit prd check" in capsys.readouterr().out
    assert main(["prd", "new", "--out", str(target)]) == 2
    assert "already exists" in capsys.readouterr().err
    assert main(["prd", "new", "--title", "Again", "--out", str(target), "--force"]) == 0
    assert "# Again" in target.read_text(encoding="utf-8")


def test_prd_check_exit_codes_and_output(tmp_path, capsys):
    weak = tmp_path / "weak.md"
    weak.write_text("# X\n\n## Success\nWe will know it worked when users are happy with it overall today.\n", encoding="utf-8")
    assert main(["prd", "check", str(weak)]) == 1          # failures -> non-zero, usable in CI
    out = capsys.readouterr().out
    assert "FAIL" in out and "no numbers" in out and "Result:" in out and "cannot tell you whether the PRD is any good" in out


def test_prd_check_strict_makes_warnings_fail(tmp_path, capsys):
    main(["prd", "new", "--out", str(tmp_path / "t.md")])
    capsys.readouterr()
    doc = (tmp_path / "t.md").read_text(encoding="utf-8")
    # fill in just enough to remove all failures, leaving placeholders (warnings) behind
    doc = doc.replace("[metric], baseline [value or \"unknown, measured in week 1\"], target [value] by [date].",
                      "completion rate, baseline 62%, target 70% by June.")
    (tmp_path / "t.md").write_text(doc, encoding="utf-8")
    assert main(["prd", "check", str(tmp_path / "t.md")]) == 0
    assert main(["prd", "check", str(tmp_path / "t.md"), "--strict"]) == 1


def test_prd_check_json_and_verbose(tmp_path, capsys):
    f = tmp_path / "p.md"
    f.write_text("# X\n\n## Problem\nUsers cannot find the export button and file support tickets about it weekly.\n", encoding="utf-8")
    main(["prd", "check", str(f), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["fail"] > 0 and data["findings"][0]["status"] in ("fail", "warn", "pass")
    main(["prd", "check", str(f), "--verbose"])
    assert "PASS" in capsys.readouterr().out


def test_prd_check_missing_file_is_a_clean_error(capsys):
    assert main(["prd", "check", "nope.md"]) == 2
    assert "file not found" in capsys.readouterr().err
