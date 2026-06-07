.PHONY: dev-api dev-sync build build-api build-sync push compose-up compose-down compose-logs

IMAGE_API ?= ghcr.io/dafrimer/procare-api:dev
IMAGE_SYNC ?= ghcr.io/dafrimer/procare-sync:dev

dev-api:
PYTHONPATH=src uvicorn api.main:app --reload --port 8080

dev-sync:
PYTHONPATH=src python src/main.py

build: build-api build-sync

build-api:
docker build -f Dockerfile.api -t $(IMAGE_API) .

build-sync:
docker build -f Dockerfile.sync -t $(IMAGE_SYNC) .

push: build
docker push $(IMAGE_API)
docker push $(IMAGE_SYNC)

compose-up:
docker compose up -d --build

compose-down:
docker compose down

compose-logs:
docker compose logs -f --tail=200