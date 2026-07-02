# match-backend

FastAPI + SQLite service running inside Docker. Python managed via `uv`.

## Stack

- **Framework**: FastAPI
- **DB**: SQLite via SQLAlchemy + Alembic migrations
- **Runtime**: Docker Compose
- **Package manager**: uv
- **Linting**: black, isort, mypy

## Common commands

```shell
make build             # Rebuild Docker image (no cache)
make up                # Start containers in background
make down              # Stop and remove containers
make bash              # Open shell inside the container
make test              # Run pytest (match/tests/)
make test unit         # Run pytest (match/tests/)
make test integration  # Run pytest (match/tests/)
make format            # Run mypy + isort + black
```

### Database / migrations

```shell
make migration name=<description>   # Autogenerate Alembic migration
make upgrade                        # Apply all pending migrations
make downgrade                      # Roll back one migration
make reset-db                       # Delete the SQLite DB file
```

### OpenAPI spec

```shell
make gen-specs    # Regenerate openapi_specs.json
```

## Tests

Tests live in `match/tests/`. Run via Docker:

```shell
docker compose run match-backend uv run pytest match/tests/ -v
```

Integration tests hit a real database — do not mock the DB layer.

## Adding dependencies

Run inside the container:

```shell
uv add "package==version"
```

## Code style

Do not add comments or docstrings unless the reason behind the code is non-obvious. Well-named identifiers are sufficient documentation.

## Local dev

Server: http://localhost:8000  
Swagger docs: http://localhost:8000/docs
