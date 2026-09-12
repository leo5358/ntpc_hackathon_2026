.PHONY: help install-backend install-frontend check-backend run-backend run-frontend build-frontend

help:
	@echo "Available commands:"
	@echo "  make install-backend   - Install Python dependencies"
	@echo "  make install-frontend  - Install NPM dependencies in web/"
	@echo "  make check-backend     - Run infra bootstrap check"
	@echo "  make run-backend       - Start FastAPI development server"
	@echo "  make run-frontend      - Start Vite development server"
	@echo "  make build-frontend    - Build static frontend assets"

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd web && npm install

check-backend:
	python3 -m infra.bootstrap --check

run-backend:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd web && npm run dev

build-frontend:
	cd web && npm run build
