import logging
import os

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


def get_config() -> Config:
    raw_config = {}
    ENV_VARS = ["ENV"]
    for env_var in ENV_VARS:
        try:
            raw_config[env_var] = os.environ[env_var]
        except KeyError:
            logging.warning(f"Environment value {env_var} not found. Skipping.")

    raw_config |= dotenv_values(ENV_DIR)  # type: ignore[arg-type]
    return Config(**raw_config)  # type: ignore[arg-type]


def configure_routing(app: FastAPI) -> None:
    app.include_router(health_api)
    app.include_router(user_api, prefix=USER_PREFIX)
    app.include_router(task_api, prefix=TASK_PREFIX)


def create_app() -> FastAPI:
    config = get_config()
    app = FastAPI()
    configure_routing(app)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
