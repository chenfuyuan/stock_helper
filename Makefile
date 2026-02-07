.PHONY: install test lint format run clean

install:
	conda env update --file environment.yml --prune

export-deps:
	conda env export --no-builds > environment.yml
	pip freeze > requirements.txt

test:
	pytest tests/

lint:
	flake8 app tests
	mypy app tests

format:
	black app tests
	isort app tests

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
