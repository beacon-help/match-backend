SERVICE = match-backend
FORMAT_TOOLS_DIR = format-tools

build:
	make down
	docker-compose build --no-cache

up:
	docker-compose up -d

stop:
	docker-compose stop

down:
	docker-compose down

bash:
	make up
	docker-compose exec -it $(SERVICE) bash

test:
	docker-compose run $(SERVICE)  pytest match/tests/ -v


format:
	make up
	docker-compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/isort.sh
	docker-compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/mypy.sh
	docker-compose exec $(SERVICE) sh $(FORMAT_TOOLS_DIR)/black.sh
