import uvicorn
from fastapi import FastAPI

from match.api.health import router as health_api
from match.api.task import router as task_api
from match.api.user import router as user_api

USER_PREFIX = "/user"
TASK_PREFIX = "/task"


def configure_routing(app: FastAPI) -> None:
    app.include_router(health_api)
    app.include_router(user_api, prefix=USER_PREFIX)
    app.include_router(task_api, prefix=TASK_PREFIX)


def create_app() -> FastAPI:
    app = FastAPI()
    configure_routing(app)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
