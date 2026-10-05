import enum
import logging
import os
from dataclasses import dataclass
from functools import cache

import match_config

from dotenv import dotenv_values

ENV_DIR = "dotenv/.env"


class Environment(enum.Enum):
    DEV = "dev"
    TEST = "test"
    LIVE = "live"


@dataclass(frozen=True)
class Config:
    ENV: Environment

    FE_HOST: str
    BACKEND_HOST: str

    DB_PATH: str

    SENTRY_ENABLED: bool
    SENTRY_DSN: str

    JWT_SECRET: str

    ACCESS_TOKEN_TTL_MIN: int
    REFRESH_TOKEN_TTL_DAYS: int


@cache
def get_config() -> Config:
    env_values: dict[str, str | None] = {}
    if "ENV" in os.environ:
        env_values["ENV"] = os.environ["ENV"]
    else:
        logging.warning("Environment value ENV not found. Skipping.")
    env_values |= dotenv_values(ENV_DIR)

    env = Environment[str(env_values["ENV"]).upper()]
    shared = match_config.get_config("backend", env.value)

    return Config(
        ENV=env,
        FE_HOST=shared.fe_host,
        BACKEND_HOST=shared.backend_host,
        DB_PATH=shared.db_path,
        SENTRY_ENABLED=shared.sentry_enabled,
        SENTRY_DSN=str(env_values["SENTRY_DSN"]),
        JWT_SECRET=str(env_values["JWT_SECRET"]),
        ACCESS_TOKEN_TTL_MIN=shared.access_token_ttl_min,
        REFRESH_TOKEN_TTL_DAYS=shared.refresh_token_ttl_days,
    )
