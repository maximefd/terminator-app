# Commandes courantes du projet. `make help` pour la liste.

PY_IMAGE := python:3.11-slim
# Le backend requiert Python 3.11 : on l'exécute dans Docker pour ne pas dépendre de la machine
BACKEND_RUN := docker run --rm -v "$(CURDIR)/backend":/app -w /app -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c

.PHONY: help setup dev-api dev-front test test-backend lint-frontend bench

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

setup: ## Prépare l'environnement local (.env + dépendances frontend)
	@test -f .env || (cp .env.example .env && echo ".env créé : pensez à remplacer les secrets")
	cd frontend && pnpm install

dev-api: ## Lance l'API (http://localhost:5001) et PostgreSQL
	docker compose up --build

dev-front: ## Lance le frontend (http://localhost:3000)
	cd frontend && pnpm dev

test: test-backend lint-frontend ## Tous les contrôles rapides

test-backend: ## Tests backend (pytest, Python 3.11 dans Docker)
	$(BACKEND_RUN) "pip install -q -r requirements.txt && pytest -q -p no:cacheprovider"

lint-frontend: ## ESLint + vérification TypeScript
	cd frontend && pnpm lint && pnpm exec tsc --noEmit

bench: ## Benchmark du générateur (20 seeds, budget 20 s) -> backend/benchmarks/latest.json
	$(BACKEND_RUN) "pip install -q -r requirements.txt && python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json"
