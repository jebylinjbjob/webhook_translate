set shell := ["powershell.exe", "-c"]

default:
    @just --list

run:
    uv run fastapi dev main.py

install:
    uv sync
