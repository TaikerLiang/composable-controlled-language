from pathlib import Path

import pytest

from controlled_english.rules import ProfileStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def store() -> ProfileStore:
    return ProfileStore([FIXTURES / "profiles"])


def shipped_rule_ids() -> list[str]:
    return sorted(ProfileStore().compose(["agent"]).rules)
