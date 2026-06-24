set shell := ["pwsh", "-c"]

default:
    @just --list

run:
    uv run fastapi dev main.py

init:
    uv sync --all-groups

fmt:
    uv run ruff format .

fmt-check:
    uv run ruff format --check --diff .

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

build:
    uv run build

test-hurl:
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from hurl
    docker compose -f docker-compose.test.yml down

docker-build:
    docker compose build

docker-up:
    docker compose up -d --build

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f
