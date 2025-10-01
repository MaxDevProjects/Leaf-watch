.PHONY: dev up down logs backend-shell test

PROJECT_ROOT := $(abspath ..)

up:
docker compose -f docker-compose.yml up --build

down:
docker compose -f docker-compose.yml down

logs:
docker compose -f docker-compose.yml logs -f

backend-shell:
docker compose -f docker-compose.yml run --rm backend bash

test:
pytest
