.PHONY: run dev lint test up down

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

lint:
	ruff check app tests

test:
	pytest -q

up:
	docker compose up --build

down:
	docker compose down