FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN apk -U upgrade && apk add bash sqlite

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /usr/app

COPY pyproject.toml uv.lock ./
COPY vendor/match-config ./vendor/match-config

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

CMD ["uv", "run", "uvicorn", "match.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
