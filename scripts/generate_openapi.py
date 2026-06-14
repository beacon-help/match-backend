from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fastapi import Depends, FastAPI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match.bootstrap import get_service
from match.infra.api.health import router as health_api
from match.infra.api.task import router as task_api
from match.infra.api.user import router as user_api


def build_app() -> FastAPI:
    app = FastAPI(title="match", version="0.1")
    app.include_router(health_api, tags=["health"])
    app.include_router(user_api, prefix="/user", dependencies=[Depends(get_service)], tags=["user"])
    app.include_router(task_api, prefix="/task", dependencies=[Depends(get_service)], tags=["task"])
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenAPI JSON for the Match API.")
    parser.add_argument(
        "--output",
        default="openapi.json",
        help="Path to write the generated OpenAPI JSON.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    openapi_spec = build_app().openapi()
    output_path.write_text(json.dumps(openapi_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
