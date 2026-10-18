"""Exit codes, output shapes and the baseline flow through the command line (PLAN § 6)."""

import json

import pytest

from controlled_english.cli import main

CONFIG = """
profiles = ["base"]

[surfaces]
runtime     = ["commands/**/*.md"]
explanatory = ["docs/**/*.md"]

[baseline]
mode = "off"
"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / ".controlled-english.toml").write_text(CONFIG)
    (tmp_path / "commands").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "commands" / "run.md").write_text(
        "---\ndescription: You should drive the stage.\n---\n\n"
        "Apply `status: ready-for-dev`\nto the issue; then wait.\n"
    )
    (tmp_path / "docs" / "guide.md").write_text("Readers should relax; it is fine.\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_lint_human_shape_and_exit_codes(repo, capsys):
    assert main(["lint"]) == 1
    out, err = capsys.readouterr()
    blocks = out.strip().split("\n\n")
    assert blocks[0].split("\n")[0] == "commands/run.md:2"
    assert blocks[0].split("\n")[1] == "BASE-M02 error"
    assert "Judgment rules not run: BASE-S08" in err
    assert "docs/guide.md" in out  # explanatory findings are reported
    assert main(["lint", "--no-fail"]) == 0
    assert main(["lint", "docs"]) == 0  # explanatory surface has no error-level rules
    capsys.readouterr()
    assert main(["lint", "--format", "compact", "commands"]) == 1
    out, _ = capsys.readouterr()
    assert out.startswith("commands/run.md:2:14: BASE-M02 error")


def test_lint_json_carries_the_contract(repo, capsys):
    assert main(["lint", "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["tokenizer_version"] == 1 and data["profiles"] == ["base"]
    assert data["rules"]["BASE-S02"] == 1
    assert data["not_run"] == ["BASE-S08"]
    assert {f["rule_id"] for f in data["findings"]} >= {"BASE-M02", "BASE-S02"}
    assert all("id" in f for f in data["findings"])


def test_severity_override_flips_the_exit_code(repo):
    cfg = repo / ".controlled-english.toml"
    cfg.write_text(
        CONFIG + '\n[rules]\n"BASE-M02" = "disabled"\n"BASE-S02" = { runtime = "warning" }\n'
    )
    assert main(["lint", "commands"]) == 0
    cfg.write_text(CONFIG + '\n[rules]\n"BASE-M02" = "disabled"\n')
    assert main(["lint", "commands"]) == 1  # the semicolon is still an error


def test_baseline_flow_new_only(repo, capsys):
    assert main(["baseline", "write"]) == 0
    assert (repo / ".controlled-english.baseline.json").exists()
    assert main(["lint", "--baseline", "new-only"]) == 0
    # re-wrapping and an unrelated edit above leave the baseline intact
    (repo / "commands" / "run.md").write_text(
        "---\ndescription: You should drive the stage.\n---\n\nNew intro.\n\n"
        "Apply `status: ready-for-dev` to the issue; then wait.\n"
    )
    assert main(["lint", "--baseline", "new-only"]) == 0
    # a changed semantic token is new prose and must pass
    (repo / "commands" / "run.md").write_text(
        "---\ndescription: You should drive the stage.\n---\n\n"
        "Apply `status: ready-for-spec`\nto the issue; then wait.\n"
    )
    assert main(["lint", "--baseline", "new-only"]) == 1
    out, err = capsys.readouterr()
    assert "(baselined)" in out and "1 new error" in err
    assert main(["baseline", "diff"]) == 0
    out, _ = capsys.readouterr()
    assert out.count("new:") == 2 and out.count("fixed:") == 2  # S02 + S03, old and new identity


def test_stale_baseline_is_refused_with_exit_2(repo, capsys):
    assert main(["baseline", "write"]) == 0
    path = repo / ".controlled-english.baseline.json"
    data = json.loads(path.read_text())
    data["rules"]["BASE-S02"] = 2
    path.write_text(json.dumps(data))
    assert main(["lint", "--baseline", "new-only"]) == 2
    assert "revision changed: BASE-S02" in capsys.readouterr().err
    data["rules"]["BASE-S02"] = 1
    data["tokenizer_version"] = 42
    path.write_text(json.dumps(data))
    assert main(["lint", "--baseline", "new-only"]) == 2
    assert "tokenizer_version" in capsys.readouterr().err
    assert main(["baseline", "diff"]) == 0  # diff still explains, never refuses
    assert "incompatible: tokenizer_version" in capsys.readouterr().out


def test_missing_baseline_in_new_only_mode_is_exit_2(repo, capsys):
    assert main(["lint", "--baseline", "new-only"]) == 2
    assert "baseline write" in capsys.readouterr().err


def test_rules_explain_judgment_and_errors(repo, capsys):
    assert main(["rules"]) == 0
    assert "BASE-S01" in capsys.readouterr().out
    assert main(["rules", "--format", "json", "--profiles", "agent"]) == 0
    assert json.loads(capsys.readouterr().out)["BASE-S08"]["check"] == "both"
    assert main(["explain", "BASE-S02"]) == 0
    assert "STE 8.1" in capsys.readouterr().out
    assert main(["explain", "NOPE-01"]) == 2
    assert main(["judgment", "export"]) == 0
    export = json.loads(capsys.readouterr().out)
    assert export[0]["rule"] == "BASE-S08" and export[0]["prompt"]
    assert main(["lint", "--profiles", "no-such"]) == 2


def test_check_fixtures_from_the_repo_root(monkeypatch, capsys):
    from .conftest import ROOT

    monkeypatch.chdir(ROOT)
    assert main(["check-fixtures"]) == 0
    assert "0 problem(s)" in capsys.readouterr().err
