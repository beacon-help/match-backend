SERVICE = match-backend
FORMAT_TOOLS_DIR = format-tools
name =

build:
	make down
	docker build . --no-cache --progress=plain

ps:
	docker compose ps
up:
	docker compose up -d

stop:
	docker compose stop

down:
	docker compose down

bash:
	make up
	docker compose exec -it $(SERVICE) bash

test:
	docker compose run $(SERVICE) uv run pytest match/tests/ -v


format:
	make up
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/mypy.sh
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/isort.sh
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/black.sh

migration:
	docker compose run $(SERVICE) uv run alembic revision -m=$(name) --autogenerate

upgrade:
	docker compose run $(SERVICE) uv run alembic upgrade head

downgrade:
	docker compose run $(SERVICE) uv run alembic downgrade -1

show:
	docker compose run $(SERVICE) uv run alembic show head

reset-db:
	docker compose run $(SERVICE) rm -f /usr/src/app/data/app.db
