"""Environment-based configuration helpers."""

import os
from typing import List


def env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw_default = "true" if default else "false"
    value = env(name, raw_default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def parse_csv(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]
