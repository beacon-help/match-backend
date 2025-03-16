SERVICE = match-backend
FORMAT_TOOLS_DIR = format-tools

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
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/isort.sh
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/mypy.sh
	docker compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/black.sh
