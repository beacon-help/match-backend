import tomllib
from pathlib import Path

import sentry_sdk
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from match.bootstrap import get_service
from match.config import Config, Environment, get_config
from match.infra.api.auth import router as auth_api
from match.infra.api.health import router as health_api
from match.infra.api.stats import router as stats_api
from match.infra.api.task import router as task_api
from match.infra.api.user import router as user_api

AUTH_PREFIX = "/user"
USER_PREFIX = "/user"
TASK_PREFIX = "/task"
STATS_PREFIX = "/stats"


def load_project_metadata() -> tuple[str, str]:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["name"], data["project"]["version"]


def configure_routing(app: FastAPI) -> None:
    app.include_router(health_api, tags=["health"])
    app.include_router(
        auth_api, prefix=AUTH_PREFIX, dependencies=[Depends(get_service)], tags=["user"]
    )
    app.include_router(
        user_api, prefix=USER_PREFIX, dependencies=[Depends(get_service)], tags=["user"]
    )
    app.include_router(
        task_api, prefix=TASK_PREFIX, dependencies=[Depends(get_service)], tags=["task"]
    )
    app.include_router(
        stats_api, prefix=STATS_PREFIX, dependencies=[Depends(get_service)], tags=["stats"]
    )


def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    config: Config = get_config()

    if config.SENTRY_ENABLED:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            send_default_pii=True,
            traces_sample_rate=1.0,
            environment=str(config.ENV),
            _experiments={"continuous_profiling_auto_start": True},
        )
    debug = config.ENV == Environment.DEV

    project_name, project_version = load_project_metadata()
    app = FastAPI(title=project_name, version=project_version, debug=debug)

    configure_cors(app)
    configure_routing(app)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
