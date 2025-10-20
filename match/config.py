import enum
import logging
import os
from dataclasses import dataclass
from typing import Any

from dotenv import dotenv_values

ENV_DIR = "dotenv/.env"


class Environment(enum.Enum):
    DEV = "dev"
    TEST = "test"
    LIVE = "live"


@dataclass(frozen=True)
class Config:
    ENV: Environment

    DB_PATH: str

    SENTRY_ENABLED: bool
    SENTRY_DSN: str


def get_config(auto_convert: bool = True) -> Config:
    raw_config: dict[str, Any] = {}
    ENV_VARS = ["ENV"]
    for env_var in ENV_VARS:
        try:
            raw_config[env_var] = os.environ[env_var]
        except KeyError:
            logging.warning(f"Environment value {env_var} not found. Skipping.")

    raw_config |= dotenv_values(ENV_DIR)  # type: ignore[arg-type]

    if auto_convert:
        for key, val in raw_config.items():
            if val == "true":
                raw_config[key] = True
            elif val == "false":
                raw_config[key] = False

        raw_config["ENV"] = Environment[raw_config["ENV"].upper()]

    return Config(**raw_config)
