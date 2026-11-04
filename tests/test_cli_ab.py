import json

from pmkit.cli import main, parse_arm


def test_parse_arm_accepts_commas_and_rejects_nonsense():
    assert parse_arm("1,200/10,000").conversions == 1200
    import pytest
    for bad in ("abc", "5", "5/", "10/5"):
        with pytest.raises(ValueError):
            parse_arm(bad)


def test_readout_text_output(capsys):
    assert main(["ab", "readout", "--control", "200/1000", "--treatment", "240/1000"]) == 0
    out = capsys.readouterr().out
    assert "+4.00 pp" in out and "relative lift +20.0%" in out and "p-value:      0.0308" in out
    assert "better than control" in out and "Valid if:" in out     # assumptions are always shown


def test_readout_json_output_is_valid_and_complete(capsys):
    assert main(["ab", "readout", "--control", "200/1000", "--treatment", "240/1000", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "SIGNIFICANT_POSITIVE"
    assert data["control"]["rate"] == 0.2 and 0 < data["p_value"] < 0.05


def test_readout_flags_sample_ratio_mismatch(capsys):
    main(["ab", "readout", "--control", "500/5000", "--treatment", "700/5400"])
    out = capsys.readouterr().out
    assert "Split check:  ALERT" in out and "Do not trust this result" in out


def test_size_text_and_duration(capsys):
    assert main(["ab", "size", "--baseline", "0.20", "--mde-abs", "0.05", "--daily-visitors", "500"]) == 0
    out = capsys.readouterr().out
    assert "1,094" in out and "2,188" in out and "5 days" in out


def test_size_relative_mde_matches_absolute(capsys):
    main(["ab", "size", "--baseline", "0.20", "--mde-rel", "0.25", "--json"])
    rel = json.loads(capsys.readouterr().out)
    main(["ab", "size", "--baseline", "0.20", "--mde-abs", "0.05", "--json"])
    assert rel["visitors_per_arm"] == json.loads(capsys.readouterr().out)["visitors_per_arm"]


def test_size_requires_exactly_one_effect_flag(capsys):
    assert main(["ab", "size", "--baseline", "0.2"]) == 2
    assert main(["ab", "size", "--baseline", "0.2", "--mde-abs", "0.05", "--mde-rel", "0.1"]) == 2
    assert "exactly one of" in capsys.readouterr().err


def test_mde_command(capsys):
    assert main(["ab", "mde", "--baseline", "0.20", "--n-per-arm", "1094"]) == 0
    assert "about 5.00 pp" in capsys.readouterr().out


def test_bad_input_gives_a_clean_error_not_a_traceback(capsys):
    assert main(["ab", "readout", "--control", "nonsense", "--treatment", "1/2"]) == 2
    assert main(["ab", "size", "--baseline", "1.5", "--mde-abs", "0.1"]) == 2
    assert capsys.readouterr().err.count("error:") == 2
