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

    JWT_SECRET: str

    ACCESS_TOKEN_TTL_MIN: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 7


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
        for int_key in ("ACCESS_TOKEN_TTL_MIN", "REFRESH_TOKEN_TTL_DAYS"):
            if int_key in raw_config:
                raw_config[int_key] = int(raw_config[int_key])

    return Config(**raw_config)
