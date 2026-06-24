set shell := ["powershell.exe", "-c"]

default:
    @just --list

run:
    uv run fastapi dev main.py

init:
    uv sync --all-groups

fmt:
    uv run ruff format .

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

docker-build:
    docker compose build

docker-up:
    docker compose up -d --build

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f
