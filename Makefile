.PHONY: dev backend frontend docker docker-build docker-down test lint clean setup help

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Start both backend + frontend in dev mode
	@echo "🚀 Starting VClip in development mode..."
	@make -j2 backend frontend

backend: ## Start backend only (with hot reload)
	@echo "🐍 Starting FastAPI backend on :8000..."
	cd backend && \
		source venv/bin/activate 2>/dev/null || true && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend only (Next.js dev server)
	@echo "⚛️  Starting Next.js frontend on :3000..."
	cd frontend && npm run dev

docker: ## Start all services with Docker Compose
	@echo "🐳 Starting VClip with Docker Compose..."
	docker compose up -d
	@echo ""
	@echo "✅ VClip is running!"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

docker-build: ## Build and start with Docker Compose
	docker compose up -d --build

docker-down: ## Stop all Docker services
	docker compose down

test: ## Run all tests
	@echo "🧪 Running backend tests..."
	cd backend && \
		source venv/bin/activate 2>/dev/null || true && \
		python -m pytest tests/ -v
	@echo ""
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test

lint: ## Run linters
	@echo "🔍 Linting backend..."
	cd backend && \
		source venv/bin/activate 2>/dev/null || true && \
		ruff check . && ruff format --check .
	@echo ""
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

clean: ## Clean temp files, caches, and build artifacts
	@echo "🧹 Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/venv 2>/dev/null || true
	rm -rf clips/* 2>/dev/null || true
	@echo "✅ Clean!"

setup: ## Run initial setup script
	chmod +x scripts/setup.sh
	./scripts/setup.sh
