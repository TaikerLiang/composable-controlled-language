"""Errors that end a run with exit code 2 (usage, config, composition, baseline)."""


class ConfigError(Exception):
    """A rule file, profile, glossary or repository configuration is invalid."""


class BaselineError(Exception):
    """A baseline file cannot be applied to the current engine, rules or profiles."""
