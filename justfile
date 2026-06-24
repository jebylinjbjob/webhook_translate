set shell := ["powershell.exe", "-c"]

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
#靜態檢查
lint:
    uv run ruff check .
lint-fix:
    uv run ruff check --fix .
#建置
build:
    uv run build
#建置docker
docker-build:
    docker compose build

docker-up:
    docker compose up -d --build

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f


ci: 
    just fmt-check
    just lint
    just build