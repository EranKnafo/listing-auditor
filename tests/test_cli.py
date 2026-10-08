import json

from listing_auditor.cli import main


def test_generate_audit_fix_roundtrip(tmp_path, capsys):
    data, truth, fixed, report = (tmp_path / n for n in ("d.json", "t.json", "f.json", "r.csv"))
    assert main(["generate", "--count", "40", "--seed", "3", "--out", str(data), "--truth", str(truth)]) == 0
    assert main(["audit", str(data), "--format", "csv", "--out", str(report)]) == 0
    assert report.read_text().startswith("listing_id,listing,score")
    original = data.read_text()
    assert main(["fix", str(data), "--write", str(fixed)]) == 0
    assert data.read_text() == original  # the source file is never touched
    assert json.loads(fixed.read_text())
    assert "re-audit average score" in capsys.readouterr().out


def test_fail_under_gates_ci(tmp_path):
    data = tmp_path / "d.json"
    main(["generate", "--count", "30", "--seed", "1", "--out", str(data)])
    assert main(["audit", str(data), "--fail-under", "101"]) == 1
    assert main(["audit", str(data), "--fail-under", "0"]) == 0


def test_benchmark_passes():
    assert main(["benchmark", "--count", "120", "--seed", "5"]) == 0
