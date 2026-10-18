"""Repository configuration: `.controlled-english.toml` (PLAN § 4.4) and file → surface."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError
from .rules import SEVERITIES, SURFACES

CONFIG_NAME = ".controlled-english.toml"
DEFAULT_BASELINE = ".controlled-english.baseline.json"
BASELINE_MODES = ("off", "new-only", "all")
PROSE_SUFFIXES = (".md", ".markdown", ".txt")
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache", "dist"}


@dataclass
class Config:
    root: Path
    profiles: list[str] = field(default_factory=lambda: ["base"])
    surfaces: dict[str, list[str]] = field(default_factory=dict)  # runtime | explanatory | ignore
    front_matter_keys: tuple[str, ...] = ("description",)
    rules: dict[str, dict[str, str]] = field(default_factory=dict)
    baseline_file: Path = field(default=None)  # type: ignore[assignment]
    baseline_mode: str = "off"
    explicit: bool = False

    def __post_init__(self):
        if self.baseline_file is None:
            self.baseline_file = self.root / DEFAULT_BASELINE


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def _severity_override(raw, rid: str, path: Path) -> dict[str, str]:
    if isinstance(raw, str):
        if raw not in SEVERITIES:
            raise ConfigError(f"{path}: rules[{rid}] {raw!r} is not a severity")
        return {s: raw for s in SURFACES}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: rules[{rid}] must be a severity or a table per surface")
    for surface, sev in raw.items():
        if surface not in SURFACES or sev not in SEVERITIES:
            raise ConfigError(f"{path}: rules[{rid}][{surface}] = {sev!r} is invalid")
    return dict(raw)


def load_config(path: Path | None, cwd: Path) -> Config:
    """Load the given file, else `cwd/.controlled-english.toml`, else the implicit default."""
    if path is None:
        candidate = cwd / CONFIG_NAME
        if not candidate.exists():
            return Config(root=cwd)
        path = candidate
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        d = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    root = path.resolve().parent
    cfg = Config(root=root, explicit=True)
    profiles = d.get("profiles", ["base"])
    if isinstance(profiles, str):
        profiles = [profiles]
    if not isinstance(profiles, list) or not all(isinstance(p, str) for p in profiles):
        raise ConfigError(f"{path}: profiles must be a list of profile names")
    cfg.profiles = profiles
    surfaces = d.get("surfaces", {})
    for key, value in surfaces.items():
        if key == "front_matter_keys":
            cfg.front_matter_keys = tuple(value)
        elif key in SURFACES or key == "ignore":
            if not isinstance(value, list):
                raise ConfigError(f"{path}: surfaces.{key} must be a list of globs")
            cfg.surfaces[key] = list(value)
        else:
            raise ConfigError(f"{path}: unknown surface {key!r}")
    cfg.rules = {rid: _severity_override(raw, rid, path) for rid, raw in d.get("rules", {}).items()}
    b = d.get("baseline", {})
    cfg.baseline_file = root / b.get("file", DEFAULT_BASELINE)
    cfg.baseline_mode = b.get("mode", "off")
    if cfg.baseline_mode not in BASELINE_MODES:
        raise ConfigError(f"{path}: baseline.mode must be one of {', '.join(BASELINE_MODES)}")
    return cfg


def surface_for(cfg: Config, rel: str) -> str | None:
    """`ignore` first, then `runtime`, then `explanatory`; None means not linted."""
    if not cfg.surfaces:
        return "explanatory" if rel.endswith(PROSE_SUFFIXES) else None
    for name in ("ignore", "runtime", "explanatory"):
        if any(glob_to_regex(g).match(rel) for g in cfg.surfaces.get(name, [])):
            return None if name == "ignore" else name
    return None


def collect_files(
    cfg: Config, paths: list[Path], force_surface: str | None = None
) -> list[tuple[Path, str, str]]:
    """(absolute path, root-relative path, surface) for every prose file under `paths`."""
    out = []
    for p in paths or [cfg.root]:
        p = p.resolve()
        candidates = (
            [p]
            if p.is_file()
            else sorted(
                q
                for q in p.rglob("*")
                if q.is_file()
                and q.suffix.lower() in PROSE_SUFFIXES
                and not (set(q.relative_to(p).parts[:-1]) & SKIP_DIRS)
            )
        )
        for q in candidates:
            try:
                rel = q.relative_to(cfg.root).as_posix()
            except ValueError:
                rel = q.as_posix()
            surface = force_surface or surface_for(cfg, rel)
            if surface is None and not (p.is_file() and not cfg.explicit):
                continue
            out.append((q, rel, surface or "explanatory"))
    return out
