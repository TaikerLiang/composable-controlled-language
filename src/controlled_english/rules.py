"""Rules, glossaries, profiles and their composition (PLAN § 4.2, § 4.3, § 4.7)."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError

SURFACES = ("runtime", "explanatory")
SEVERITIES = ("error", "warning", "advisory", "disabled")
CHECKS = ("deterministic", "judgment", "both")
KINDS = ("length", "char", "phrase", "pattern", "list", "glossary", "insertion", "judgment")
SOURCES = ("ste-derived", "framework", "project")
MODALITIES = ("obligation", "prohibition", "permission", "possibility")
CLAUSES = ("action", "any")

_RULE_REQUIRED = (
    "id",
    "revision",
    "title",
    "layer",
    "check",
    "kind",
    "source",
    "severity",
    "message",
    "rationale",
)


@dataclass(frozen=True)
class Rule:
    id: str
    revision: int
    title: str
    layer: str
    check: str
    kind: str
    source: str
    lineage: tuple[str, ...]
    inspired_by: tuple[str, ...]
    severity: dict[str, str]
    modality: tuple[str, ...]
    message: str
    rationale: str
    params: dict
    examples: tuple[dict, ...]
    judgment_prompt: str | None
    path: Path


@dataclass
class Concept:
    name: str
    canonical: str | None
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]
    meaning: str
    surfaces: tuple[str, ...]
    clause: str
    profile: str


@dataclass
class Glossary:
    concepts: dict[str, Concept] = field(default_factory=dict)
    actors: list[str] = field(default_factory=list)
    imperative_verbs: list[str] = field(default_factory=list)
    modality: dict[str, list[str]] = field(default_factory=dict)
    allow: dict[str, list[str]] = field(default_factory=dict)

    def merge(self, other: Glossary, other_profile: str) -> None:
        for name, c in other.concepts.items():
            mine = self.concepts.get(name)
            if mine is None:
                self.concepts[name] = Concept(**vars(c))
                continue
            if mine.canonical and c.canonical and mine.canonical != c.canonical:
                raise ConfigError(
                    f"glossary concept {name!r}: profile {mine.profile!r} says canonical "
                    f"{mine.canonical!r}, profile {other_profile!r} says {c.canonical!r}"
                )
            mine.canonical = mine.canonical or c.canonical
            mine.allowed = _union(mine.allowed, c.allowed)
            mine.forbidden = _union(mine.forbidden, c.forbidden)
            mine.meaning = c.meaning or mine.meaning
            mine.surfaces = c.surfaces
            mine.clause = c.clause
        self.actors = list(_union(self.actors, other.actors))
        self.imperative_verbs = list(_union(self.imperative_verbs, other.imperative_verbs))
        for cat, words in other.modality.items():
            have = self.modality.get(cat, [])
            if have and words and set(have) != set(words):
                raise ConfigError(
                    f"modality {cat!r}: already bound to {have}, profile {other_profile!r} "
                    f"binds {words}"
                )
            self.modality[cat] = list(words) if words else have
        for rule_id, words in other.allow.items():
            self.allow[rule_id] = list(_union(self.allow.get(rule_id, []), words))


def _union(a, b) -> tuple:
    out = list(a)
    for x in b:
        if x not in out:
            out.append(x)
    return tuple(out)


@dataclass
class Profile:
    name: str
    extends: tuple[str, ...]
    severity: dict[str, dict[str, str]]
    rules: dict[str, Rule]
    glossary: Glossary
    path: Path


@dataclass
class RuleSet:
    """The effective result of composing profiles."""

    profiles: tuple[str, ...]
    rules: dict[str, Rule]
    severity: dict[str, dict[str, str]]
    glossary: Glossary

    def severity_for(
        self, rule_id: str, surface: str, overrides: dict[str, dict[str, str]] | None = None
    ) -> str:
        if overrides and rule_id in overrides and surface in overrides[rule_id]:
            return overrides[rule_id][surface]
        return self.severity.get(rule_id, {}).get(surface, "disabled")

    def revisions(self) -> dict[str, int]:
        return {rid: r.revision for rid, r in sorted(self.rules.items())}

    def digest(self) -> str:
        payload = json.dumps(
            {"profiles": list(self.profiles), "rules": self.revisions()}, sort_keys=True
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- loading ---------------------------------------------------------------------


def default_roots() -> list[Path]:
    here = Path(__file__).resolve().parent
    shipped = here / "profiles"
    if shipped.is_dir():
        return [shipped]
    return [here.parents[1] / "profiles"]


def _load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e


def _require(data: dict, keys, path: Path) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise ConfigError(f"{path}: missing field(s) {', '.join(missing)}")


def _enum(value, allowed, what: str, path: Path) -> None:
    if value not in allowed:
        raise ConfigError(f"{path}: {what} {value!r} is not one of {', '.join(allowed)}")


def _severity_table(raw, path: Path, what: str) -> dict[str, str]:
    if isinstance(raw, str):
        _enum(raw, SEVERITIES, what, path)
        return {s: raw for s in SURFACES}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: {what} must be a severity or a table per surface")
    out = {}
    for surface, sev in raw.items():
        _enum(surface, SURFACES, f"{what} surface", path)
        _enum(sev, SEVERITIES, f"{what}[{surface}]", path)
        out[surface] = sev
    return out


def load_rule(path: Path, profile_name: str) -> Rule:
    d = _load_toml(path)
    _require(d, _RULE_REQUIRED, path)
    rid = d["id"]
    if path.stem != rid:
        raise ConfigError(f"{path}: file name must be {rid}.toml")
    if not isinstance(d["revision"], int) or d["revision"] < 1:
        raise ConfigError(f"{path}: revision must be a positive integer")
    if d["layer"] != profile_name:
        raise ConfigError(
            f"{path}: layer {d['layer']!r} must equal the profile name {profile_name!r}"
        )
    _enum(d["check"], CHECKS, "check", path)
    _enum(d["kind"], KINDS, "kind", path)
    _enum(d["source"], SOURCES, "source", path)
    lineage = tuple(d.get("lineage", ()))
    inspired = tuple(d.get("inspired_by", ()))
    if d["source"] == "ste-derived":
        if not lineage:
            raise ConfigError(f"{path}: source ste-derived requires lineage")
        if inspired:
            raise ConfigError(f"{path}: source ste-derived uses lineage, not inspired_by")
    elif lineage:
        raise ConfigError(f"{path}: source {d['source']!r} may not claim lineage; use inspired_by")
    severity = _severity_table(d["severity"], path, "severity")
    for s in SURFACES:
        severity.setdefault(s, "disabled")
    modality = tuple(d.get("modality", ()))
    for m in modality:
        _enum(m, MODALITIES, "modality", path)
    judgment = d.get("judgment", {})
    prompt = judgment.get("prompt") if isinstance(judgment, dict) else None
    if d["check"] in ("judgment", "both") and not prompt:
        raise ConfigError(f"{path}: check {d['check']!r} requires [judgment].prompt")
    if d["check"] == "deterministic" and prompt:
        raise ConfigError(f"{path}: a deterministic rule has no [judgment] table")
    if (d["kind"] == "judgment") != (d["check"] == "judgment"):
        raise ConfigError(f"{path}: kind judgment and check judgment go together")
    examples = tuple(d.get("examples", ()))
    for ex in examples:
        if not isinstance(ex, dict) or "bad" not in ex:
            raise ConfigError(f"{path}: every [[examples]] entry needs a bad sentence")
    return Rule(
        id=rid,
        revision=d["revision"],
        title=d["title"],
        layer=d["layer"],
        check=d["check"],
        kind=d["kind"],
        source=d["source"],
        lineage=lineage,
        inspired_by=inspired,
        severity=severity,
        modality=modality,
        message=d["message"],
        rationale=d["rationale"],
        params=d.get("params", {}),
        examples=examples,
        judgment_prompt=prompt,
        path=path,
    )


def load_glossary(path: Path, profile_name: str) -> Glossary:
    if not path.exists():
        return Glossary()
    d = _load_toml(path)
    g = Glossary(
        actors=list(d.get("actors", [])),
        imperative_verbs=list(d.get("imperative_verbs", [])),
        modality={k: list(v) for k, v in d.get("modality", {}).items()},
        allow={k: list(v) for k, v in d.get("allow", {}).items()},
    )
    for cat in g.modality:
        _enum(cat, MODALITIES, "modality category", path)
    for c in d.get("concept", []):
        _require(c, ("name",), path)
        scope = c.get("scope", {})
        surfaces = tuple(scope.get("surfaces", SURFACES))
        for s in surfaces:
            _enum(s, SURFACES, f"concept {c['name']!r} scope surface", path)
        clause = scope.get("clause", "any")
        _enum(clause, CLAUSES, f"concept {c['name']!r} scope clause", path)
        if c["name"] in g.concepts:
            raise ConfigError(f"{path}: concept {c['name']!r} defined twice")
        g.concepts[c["name"]] = Concept(
            name=c["name"],
            canonical=c.get("canonical"),
            allowed=tuple(c.get("allowed", ())),
            forbidden=tuple(c.get("forbidden", ())),
            meaning=c.get("meaning", ""),
            surfaces=surfaces,
            clause=clause,
            profile=profile_name,
        )
    return g


class ProfileStore:
    """Finds profile directories in one or more roots and composes them."""

    def __init__(self, roots: list[Path] | None = None):
        self.roots = list(roots or []) + default_roots()
        self._cache: dict[str, Profile] = {}

    def names(self) -> list[str]:
        seen = []
        for root in self.roots:
            if root.is_dir():
                for p in sorted(root.iterdir()):
                    if (p / "profile.toml").exists() and p.name not in seen:
                        seen.append(p.name)
        return seen

    def load(self, name: str) -> Profile:
        if name in self._cache:
            return self._cache[name]
        for root in self.roots:
            path = root / name / "profile.toml"
            if path.exists():
                break
        else:
            raise ConfigError(
                f"profile {name!r} not found under " + ", ".join(str(r) for r in self.roots)
            )
        d = _load_toml(path)
        if d.get("name", name) != name:
            raise ConfigError(f"{path}: name {d.get('name')!r} must equal the directory name")
        rules: dict[str, Rule] = {}
        rules_dir = path.parent / "rules"
        if rules_dir.is_dir():
            for rp in sorted(rules_dir.glob("*.toml")):
                rule = load_rule(rp, name)
                rules[rule.id] = rule
        severity = {
            rid: _severity_table(raw, path, f"severity[{rid}]")
            for rid, raw in d.get("severity", {}).items()
        }
        profile = Profile(
            name=name,
            extends=tuple(d.get("extends", ())),
            severity=severity,
            rules=rules,
            glossary=load_glossary(path.parent / "glossary.toml", name),
            path=path.parent,
        )
        self._cache[name] = profile
        return profile

    def resolve(self, names: list[str]) -> list[str]:
        """Depth-first, parents first, left to right, each profile once at its first position."""
        order: list[str] = []

        def visit(name: str, chain: tuple[str, ...]) -> None:
            if name in chain:
                raise ConfigError("profile extends cycle: " + " → ".join(chain + (name,)))
            for parent in self.load(name).extends:
                visit(parent, chain + (name,))
            if name not in order:
                order.append(name)

        for n in names:
            visit(n, ())
        return order

    def compose(self, names: list[str]) -> RuleSet:
        order = self.resolve(names)
        rules: dict[str, Rule] = {}
        owner: dict[str, str] = {}
        severity: dict[str, dict[str, str]] = {}
        glossary = Glossary()
        for name in order:
            p = self.load(name)
            for rid, rule in p.rules.items():
                if rid in rules:
                    raise ConfigError(f"rule {rid} is defined by both {owner[rid]!r} and {name!r}")
                rules[rid] = rule
                owner[rid] = name
                severity[rid] = dict(rule.severity)
            glossary.merge(p.glossary, name)
        for name in order:
            for rid, table in self.load(name).severity.items():
                if rid not in rules:
                    raise ConfigError(f"profile {name!r} overrides unknown rule {rid}")
                severity[rid].update(table)
        return RuleSet(profiles=tuple(order), rules=rules, severity=severity, glossary=glossary)
