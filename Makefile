IMAGE ?= ghcr.io/$(shell git config user.name | tr '[:upper:]' '[:lower:]')/procare-sync
TAG ?= latest

.PHONY: dev build push compose-up compose-down lint

dev:
	RUN_ONCE=true PYTHONPATH=src python src/main.py

build:
	docker build -t $(IMAGE):$(TAG) .

push:
	docker push $(IMAGE):$(TAG)

compose-up:
	docker compose up --build

compose-down:
	docker compose down

lint:
	python -m py_compile src/config.py src/auth.py src/client.py src/db.py src/main.py \
		src/models/__init__.py \
		src/sync/base.py src/sync/runner.py src/sync/kids.py \
		src/sync/daily_activities.py src/sync/rooms.py \
		src/sync/contacts.py src/sync/staff.py
