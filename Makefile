PYTHON ?= python3.11
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install train test api demo docker-build docker-up docker-down podman-build

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

train:
	$(PY) backend/scripts/train_model.py

test:
	$(PY) -m pytest

api:
	$(VENV)/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

demo:
	$(PY) demo/serve_demo.py

docker-build:
	docker build -t clauseguard .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

podman-build:
	podman build -t clauseguard .
