PYTHON := $(shell if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; else echo python3; fi)
UVICORN := $(shell if [ -f .venv/bin/uvicorn ]; then echo .venv/bin/uvicorn; else echo uvicorn; fi)

help:
	@echo "Available commands:"
	@echo "  make install-backend     - Install Python dependencies"
	@echo "  make install-frontend    - Install NPM dependencies in web/"
	@echo "  make check-backend       - Run infra bootstrap check"
	@echo "  make check-bedrock       - Test AWS Bedrock connection & Claude model"
	@echo "  make run-backend         - Start FastAPI development server"
	@echo "  make run-frontend        - Start Vite development server"
	@echo "  make build-frontend      - Build static frontend assets"
	@echo "  make test-opinion-crawler - Run end-to-end opinion crawler & Bedrock test"

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd web && npm install

check-backend:
	$(PYTHON) -m infra.bootstrap --check

check-bedrock:
	$(PYTHON) -m infra.check_bedrock

run-backend:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd web && npm run dev

build-frontend:
	cd web && npm run build

test-opinion-crawler:
	$(PYTHON) -m pipeline.nlp.service --name "新北市北大非營利幼兒園" --id "N07" --district "三峽區"
