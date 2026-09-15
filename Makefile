# Commandes courantes du projet. `make help` pour la liste.

PY_IMAGE := python:3.11-slim
# Le backend requiert Python 3.11 : on l'exécute dans Docker pour ne pas dépendre de la machine
BACKEND_RUN := docker run --rm -v "$(CURDIR)/backend":/app -w /app -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c
# Outils (tools/) : dépôt complet monté, commandes lancées depuis sa racine
TOOLS_RUN := docker run --rm -v "$(CURDIR)":/repo -w /repo -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c

.PHONY: help setup dev-api dev-front test test-backend test-tools lint-frontend bench \
	lexicon-download lexicon-build lexicon-export lexicon-stats \
	curator curator-bg curator-stop curator-logs curator-check curator-urls

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

CURATOR_CONTAINER := terminator_curator
CURATOR_DOCKER_ARGS := -p 8765:8765 -v "$(CURDIR)":/repo -w /repo --env-file .env -e TZ=Europe/Paris \
	-e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c "pip install -q -r tools/curator/requirements.txt && python -m tools.curator"

curator-check:
	@test -f data/lexicon/build/lexicon.sqlite || (echo "Base absente : lancez d'abord make lexicon-build" && exit 1)
	@grep -q '^CURATOR_PIN=......' .env 2>/dev/null || (echo "Définissez CURATOR_PIN (6 caractères minimum) dans .env" && exit 1)

curator-urls:
	@echo "Curateur sur cet ordinateur : http://localhost:8765"
	@# Adresse de l'interface qui porte la route par défaut (Wi-Fi ou Ethernet selon la machine)
	@echo "Téléphone sur le même Wi-Fi : http://$$(ipconfig getifaddr $$(route -n get default 2>/dev/null | awk '/interface:/{print $$2}') 2>/dev/null || echo IP-du-Mac):8765"
	@TS=$$( (tailscale ip -4 || /Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4) 2>/dev/null | head -n 1 ); \
		if [ -n "$$TS" ]; then echo "Partout avec Tailscale     : http://$$TS:8765"; fi

curator: curator-check curator-urls ## Mini-app de curation au premier plan (Ctrl+C pour arrêter)
	docker run --rm -it $(CURATOR_DOCKER_ARGS)

curator-bg: curator-check ## Mini-app de curation en arrière-plan, relancée avec Docker
	@docker rm -f $(CURATOR_CONTAINER) >/dev/null 2>&1 || true
	@docker run -d --name $(CURATOR_CONTAINER) --restart unless-stopped $(CURATOR_DOCKER_ARGS) >/dev/null
	@echo "Curateur lancé en arrière-plan (make curator-stop pour l'arrêter, make curator-logs pour son journal)."
	@$(MAKE) --no-print-directory curator-urls

curator-stop: ## Arrête la mini-app de curation lancée en arrière-plan
	docker rm -f $(CURATOR_CONTAINER)

curator-logs: ## Journal de la mini-app de curation en arrière-plan
	docker logs -f $(CURATOR_CONTAINER)

lint-frontend: ## ESLint + vérification TypeScript
	cd frontend && pnpm lint && pnpm exec tsc --noEmit

bench: ## Benchmark du générateur (20 seeds, budget 20 s) -> backend/benchmarks/latest.json
	$(BACKEND_RUN) "pip install -q -r requirements.txt && python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json"
