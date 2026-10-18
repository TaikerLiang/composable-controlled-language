"""Repository configuration, surfaces and file discovery (PLAN § 4.4)."""

from pathlib import Path

import pytest

from controlled_english.config import collect_files, glob_to_regex, load_config, surface_for
from controlled_english.errors import ConfigError

CONFIG = """
profiles = ["agent"]

[surfaces]
runtime     = ["commands/**/*.md", "agents/*.md", "references/*-brief.md"]
explanatory = ["README.md", "docs/**/*.md", "references/*.md"]
ignore      = ["CHANGELOG.md", "evals/**", "docs/learn/**"]
front_matter_keys = ["description", "summary"]

[rules]
"BASE-V01" = "disabled"
"BASE-S02" = { runtime = "advisory" }

[baseline]
file = "baseline.json"
mode = "new-only"
"""


def test_glob_to_regex():
    assert glob_to_regex("commands/**/*.md").match("commands/a.md")
    assert glob_to_regex("commands/**/*.md").match("commands/x/y/a.md")
    assert not glob_to_regex("commands/*.md").match("commands/x/a.md")
    assert glob_to_regex("evals/**").match("evals/lint/c.md")
    assert glob_to_regex("references/*-brief.md").match("references/qa-brief.md")
    assert not glob_to_regex("references/*-brief.md").match("references/brief.md")


def test_implicit_default_lints_every_markdown_file_as_explanatory(tmp_path):
    cfg = load_config(None, tmp_path)
    assert cfg.profiles == ["base"] and not cfg.explicit
    assert surface_for(cfg, "any/where.md") == "explanatory"
    assert surface_for(cfg, "script.py") is None


def test_explicit_config_surfaces_overrides_and_baseline(tmp_path):
    (tmp_path / ".controlled-english.toml").write_text(CONFIG)
    cfg = load_config(None, tmp_path)
    assert cfg.profiles == ["agent"] and cfg.explicit
    assert surface_for(cfg, "commands/integrate.md") == "runtime"
    assert surface_for(cfg, "references/qa-brief.md") == "runtime"
    assert surface_for(cfg, "references/workflow.md") == "explanatory"
    assert surface_for(cfg, "docs/learn/quiz.md") is None  # ignore wins over explanatory
    assert surface_for(cfg, "evals/x.md") is None
    assert surface_for(cfg, "hooks/x.md") is None  # unmatched → not linted
    assert cfg.front_matter_keys == ("description", "summary")
    assert cfg.rules == {
        "BASE-V01": {"runtime": "disabled", "explanatory": "disabled"},
        "BASE-S02": {"runtime": "advisory"},
    }
    assert cfg.baseline_file == tmp_path / "baseline.json"
    assert cfg.baseline_mode == "new-only"


def test_invalid_config_values_are_errors(tmp_path):
    p = tmp_path / ".controlled-english.toml"
    p.write_text('[baseline]\nmode = "sometimes"\n')
    with pytest.raises(ConfigError, match="baseline.mode"):
        load_config(None, tmp_path)
    p.write_text('[rules]\n"BASE-S02" = "loud"\n')
    with pytest.raises(ConfigError, match="not a severity"):
        load_config(None, tmp_path)
    p.write_text('[surfaces]\nstrict = ["x"]\n')
    with pytest.raises(ConfigError, match="unknown surface"):
        load_config(None, tmp_path)
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.toml", tmp_path)


def test_collect_files_skips_hidden_and_unmatched(tmp_path):
    (tmp_path / ".controlled-english.toml").write_text(CONFIG)
    for rel in ("commands/a.md", "docs/b.md", "evals/c.md", "hooks/d.md", ".git/e.md", "x.py"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("Hi.\n")
    cfg = load_config(None, tmp_path)
    got = [(rel, surface) for _, rel, surface in collect_files(cfg, [tmp_path])]
    assert got == [("commands/a.md", "runtime"), ("docs/b.md", "explanatory")]
    forced = collect_files(cfg, [tmp_path / "hooks" / "d.md"], force_surface="runtime")
    assert [(rel, s) for _, rel, s in forced] == [("hooks/d.md", "runtime")]
    assert [Path(a).name for a, _, _ in collect_files(cfg, [tmp_path / "hooks" / "d.md"])] == []
