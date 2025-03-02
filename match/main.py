import logging
import os

import sentry_sdk
import uvicorn
from fastapi import FastAPI

from dotenv import dotenv_values
from match.config import Config
from match.infra.api.health import router as health_api
from match.infra.api.task import router as task_api
from match.infra.api.user import router as user_api

USER_PREFIX = "/user"
TASK_PREFIX = "/task"

ENV_DIR = "dotenv/.env"


def get_config(auto_convert: bool = True) -> Config:
    raw_config = {}
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
                raw_config[key] = True  # type: ignore[assignment]
            elif val == "false":
                raw_config[key] = False  # type: ignore[assignment]

    return Config(**raw_config)  # type: ignore[arg-type]


def configure_routing(app: FastAPI) -> None:
    app.include_router(health_api)
    app.include_router(user_api, prefix=USER_PREFIX)
    app.include_router(task_api, prefix=TASK_PREFIX)


def create_app() -> FastAPI:
    config: Config = get_config()

    if config.SENTRY_ENABLED:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for tracing.
            traces_sample_rate=1.0,
            environment=config.ENV,
            _experiments={
                # Set continuous_profiling_auto_start to True
                # to automatically start the profiler on when
                # possible.
                "continuous_profiling_auto_start": True,
            },
        )

    app = FastAPI()
    configure_routing(app)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
