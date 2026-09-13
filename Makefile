PYTHON := $(shell if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; else echo python3; fi)
UVICORN := $(shell if [ -f .venv/bin/uvicorn ]; then echo .venv/bin/uvicorn; else echo uvicorn; fi)

help:
	@echo "Available commands:"
	@echo "  make install-backend     - Install Python dependencies"
	@echo "  make install-frontend    - Install NPM dependencies in web/"
	@echo "  make check-backend       - Run infra bootstrap check"
	@echo "  make check-bedrock       - Test AWS Bedrock connection & Claude model"
	@echo "  make check-s3-dataset    - Test private S3 dataset access"
	@echo "  make download-s3-dataset - Download and validate the complete dataset ZIP"
	@echo "  make run-backend         - Start FastAPI development server"
	@echo "  make run-frontend        - Start Vite development server"
	@echo "  make build-frontend      - Build static frontend assets"
	@echo "  make test-opinion-crawler - Run end-to-end opinion crawler & Bedrock test"
	@echo "  make smoke-backend       - Offline endpoint smoke tests (no AWS needed)"
	@echo "  make deploy-api          - Deploy backend to Lambda + API Gateway"
	@echo "  make deploy-web          - Deploy frontend to S3 + CloudFront (needs API_URL)"
	@echo "  make deploy              - Deploy backend then frontend"
	@echo "  make verify-deploy       - Verify deployed Lambda by direct invoke"

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd web && npm install

check-backend:
	$(PYTHON) -m infra.bootstrap --check

check-bedrock:
	$(PYTHON) -m infra.check_bedrock

check-s3-dataset:
	$(PYTHON) -m infra.check_s3_dataset

download-s3-dataset:
	$(PYTHON) -m infra.check_s3_dataset --download

run-backend:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd web && npm run dev

build-frontend:
	cd web && npm run build

STAGE ?= dev

smoke-backend:
	$(PYTHON) -m infra.smoke_local

deploy-api:
	$(PYTHON) -m infra.deploy_api --stage $(STAGE) --output-url-file .api_url

deploy-web:
	$(PYTHON) -m infra.deploy_web --stage $(STAGE) --api-url "$(shell cat .api_url 2>/dev/null)"

deploy: deploy-api verify-deploy deploy-web

verify-deploy:
	$(PYTHON) -m infra.verify_deploy --stage $(STAGE)

test-opinion-crawler:
	$(PYTHON) -m pipeline.nlp.service --name "新北市北大非營利幼兒園" --id "N07" --district "三峽區"
