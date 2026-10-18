"""A finding and its baseline identity (PLAN § 4.5)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass


@dataclass
class Finding:
    rule_id: str
    revision: int
    file: str
    line: int
    col: int
    surface: str
    severity: str
    message: str
    match: str
    sentence: str  # canonical sentence
    kind: str = "body"
    baselined: bool = False

    @property
    def identity(self) -> str:
        payload = "\n".join([self.rule_id, str(self.revision), self.file, self.sentence])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_json(self) -> dict:
        d = asdict(self)
        d["id"] = self.identity
        return d
