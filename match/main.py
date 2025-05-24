import sentry_sdk
import uvicorn
from fastapi import Depends, FastAPI

from match.bootstrap import get_service
from match.config import Config, get_config
from match.infra.api.health import router as health_api
from match.infra.api.task import router as task_api
from match.infra.api.user import router as user_api

USER_PREFIX = "/user"
TASK_PREFIX = "/task"


def configure_routing(app: FastAPI) -> None:
    app.include_router(health_api)
    app.include_router(user_api, prefix=USER_PREFIX, dependencies=[Depends(get_service)])
    app.include_router(task_api, prefix=TASK_PREFIX, dependencies=[Depends(get_service)])


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
            environment=str(config.ENV),
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
