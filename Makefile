
VENV=.venv
PY=$(VENV)/Scripts/python.exe
PIP=$(VENV)/Scripts/pip.exe

.PHONY: venv install install-constraints test run docker-build docker-run clean

venv:
	python -m venv $(VENV)

install: venv
	$(PY) -m pip install --upgrade pip
	$(PIP) install -e . -c Resources/constraints.txt

install-constraints: venv
	$(PY) -m pip install --upgrade pip
	$(PIP) install -r Resources/requirements.txt -c Resources/constraints.txt

test: venv
	$(PY) -m pytest -q

run: venv
	$(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t vibe-coding:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env -v ${PWD}:/app vibe-coding:latest

clean:
	if exist $(VENV) rmdir /s /q $(VENV)
