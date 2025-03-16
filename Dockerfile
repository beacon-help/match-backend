FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN apk -U upgrade && apk add bash

COPY pyproject.toml uv.lock .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

WORKDIR /usr/app

CMD ["uv", "run", "uvicorn", "match.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
