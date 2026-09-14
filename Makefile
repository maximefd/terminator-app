# Commandes courantes du projet. `make help` pour la liste.

PY_IMAGE := python:3.11-slim
# Le backend requiert Python 3.11 : on l'exécute dans Docker pour ne pas dépendre de la machine
BACKEND_RUN := docker run --rm -v "$(CURDIR)/backend":/app -w /app -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c
# Outils (tools/) : dépôt complet monté, commandes lancées depuis sa racine
TOOLS_RUN := docker run --rm -v "$(CURDIR)":/repo -w /repo -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c

.PHONY: help setup dev-api dev-front test test-backend test-tools lint-frontend bench \
	lexicon-download lexicon-build lexicon-export lexicon-stats curator

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

setup: ## Prépare l'environnement local (.env + dépendances frontend)
	@test -f .env || (cp .env.example .env && echo ".env créé : pensez à remplacer les secrets")
	cd frontend && pnpm install

dev-api: ## Lance l'API (http://localhost:5001) et PostgreSQL
	docker compose up --build

dev-front: ## Lance le frontend (http://localhost:3000)
	cd frontend && pnpm dev

test: test-backend test-tools lint-frontend ## Tous les contrôles rapides

test-backend: ## Tests backend (pytest, Python 3.11 dans Docker)
	$(BACKEND_RUN) "pip install -q -r requirements.txt && pytest -q -p no:cacheprovider"

test-tools: ## Tests des outils (pipeline du lexique)
	$(TOOLS_RUN) "pip install -q pytest -r tools/curator/requirements.txt && pytest -q -p no:cacheprovider tools"

lexicon-download: ## Télécharge et vérifie les sources du lexique (~411 Mo)
	$(TOOLS_RUN) "python -m tools.lexicon download"

lexicon-build: ## Construit data/lexicon/build/lexicon.sqlite (plusieurs minutes)
	$(TOOLS_RUN) "python -m tools.lexicon build"

lexicon-export: ## Exporte le lexique curé (data/lexicon/build/lexique_cure.csv)
	$(TOOLS_RUN) "python -m tools.lexicon export"

lexicon-stats: ## Avancement de la curation
	$(TOOLS_RUN) "python -m tools.lexicon stats"

curator: ## Mini-app de curation (ordinateur et téléphone sur le même Wi-Fi)
	@test -f data/lexicon/build/lexicon.sqlite || (echo "Base absente : lancez d'abord make lexicon-build" && exit 1)
	@grep -q '^CURATOR_PIN=..' .env 2>/dev/null || (echo "Définissez CURATOR_PIN (6 caractères minimum) dans .env" && exit 1)
	@echo "Curateur : http://localhost:8765  ·  téléphone : http://$$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d' ' -f1):8765"
	docker run --rm -it -p 8765:8765 -v "$(CURDIR)":/repo -w /repo --env-file .env -e TZ=Europe/Paris \
		-e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c "pip install -q -r tools/curator/requirements.txt && python -m tools.curator"

lint-frontend: ## ESLint + vérification TypeScript
	cd frontend && pnpm lint && pnpm exec tsc --noEmit

bench: ## Benchmark du générateur (20 seeds, budget 20 s) -> backend/benchmarks/latest.json
	$(BACKEND_RUN) "pip install -q -r requirements.txt && python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json"
