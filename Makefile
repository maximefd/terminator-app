# Commandes courantes du projet. `make help` pour la liste.

PY_IMAGE := python:3.11-slim
# Le backend requiert Python 3.11 : on l'exécute dans Docker pour ne pas dépendre de la machine
BACKEND_RUN := docker run --rm -v "$(CURDIR)/backend":/app -w /app -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c
# Outils (tools/) : dépôt complet monté, commandes lancées depuis sa racine
TOOLS_RUN := docker run --rm -v "$(CURDIR)":/repo -w /repo -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c

.PHONY: help setup dev-api dev-front test test-backend test-tools test-e2e lint-backend lint-frontend bench bench-load layouts-check db-backup db-restore-check \
	lexicon-download lexicon-build lexicon-export lexicon-stats \
	curator curator-bg curator-stop curator-logs curator-check curator-urls \
	preview-remote

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

setup: ## Prépare l'environnement local (.env + dépendances frontend)
	@test -f .env || (cp .env.example .env && echo ".env créé : pensez à remplacer les secrets")
	cd frontend && pnpm install

dev-api: ## Lance l'API (http://localhost:5001) et PostgreSQL
	docker compose up --build

dev-front: ## Lance le frontend (http://localhost:3000)
	cd frontend && pnpm dev

test: lint-backend test-backend test-tools lint-frontend ## Tous les contrôles rapides

lint-backend: ## Lint Python du backend et des outils (ruff, règles dans ruff.toml)
	$(TOOLS_RUN) "pip install -q ruff==0.16.7 && ruff check backend tools"

test-backend: ## Tests backend (pytest, Python 3.11 dans Docker)
	$(BACKEND_RUN) "pip install -q -r requirements.txt && pytest -q -p no:cacheprovider"

layouts-check: ## Vérifie tous les layouts du catalogue (backend/layouts)
	$(BACKEND_RUN) "python check_layouts.py"

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
	@test -f data/lexicon/build/lexicon.sqlite || echo "Base du lexique absente : seul l'éditeur de layouts sera disponible (make lexicon-build pour trier les mots)."
	@grep -q '^CURATOR_PIN=......' .env 2>/dev/null || (echo "Définissez CURATOR_PIN (6 caractères minimum) dans .env" && exit 1)

curator-urls:
	@echo "Curateur sur cet ordinateur : http://localhost:8765"
	@echo "Éditeur de layouts          : http://localhost:8765/layouts"
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

PREVIEW_TMP := /tmp/terminator-preview-remote

preview-remote: ## Tunnel temporaire (cloudflared) pour faire tester l'app à quelqu'un à distance, sans déploiement
	@command -v cloudflared >/dev/null || (echo "cloudflared manquant : brew install cloudflared" && exit 1)
	@test -f .env || (echo ".env manquant : lancez d'abord 'make setup'" && exit 1)
	@mkdir -p $(PREVIEW_TMP)
	@rm -f $(PREVIEW_TMP)/api.log $(PREVIEW_TMP)/front.log
	@echo "Ouverture des tunnels (cloudflared)..." ; \
	cloudflared tunnel --url http://localhost:5001 >$(PREVIEW_TMP)/api.log 2>&1 & API_PID=$$!; \
	cloudflared tunnel --url http://localhost:3000 >$(PREVIEW_TMP)/front.log 2>&1 & FRONT_PID=$$!; \
	API_URL=""; FRONT_URL=""; \
	for i in $$(seq 1 30); do \
		[ -z "$$API_URL" ] && API_URL=$$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' $(PREVIEW_TMP)/api.log | head -n1); \
		[ -z "$$FRONT_URL" ] && FRONT_URL=$$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' $(PREVIEW_TMP)/front.log | head -n1); \
		[ -n "$$API_URL" ] && [ -n "$$FRONT_URL" ] && break; \
		sleep 1; \
	done; \
	if [ -z "$$API_URL" ] || [ -z "$$FRONT_URL" ]; then \
		echo "Échec : les tunnels n'ont pas démarré à temps (voir $(PREVIEW_TMP)/*.log)"; \
		kill $$API_PID $$FRONT_PID 2>/dev/null; \
		exit 1; \
	fi; \
	echo ""; \
	echo "URL à donner à la personne qui teste : $$FRONT_URL"; \
	echo "(API tunnel, usage interne du frontend : $$API_URL)"; \
	echo ""; \
	cp .env $(PREVIEW_TMP)/env.bak; \
	if grep -q '^CORS_ORIGINS=' .env; then \
		CURRENT=$$(grep '^CORS_ORIGINS=' .env | head -n1 | cut -d= -f2-); \
		case ",$$CURRENT," in \
			*",$$FRONT_URL,"*) ;; \
			*) sed -i '' "s#^CORS_ORIGINS=.*#CORS_ORIGINS=$$CURRENT,$$FRONT_URL#" .env ;; \
		esac; \
	else \
		echo "CORS_ORIGINS=http://localhost:3000,$$FRONT_URL" >> .env; \
	fi; \
	docker compose up -d api; \
	trap "kill $$API_PID $$FRONT_PID 2>/dev/null; mv -f $(PREVIEW_TMP)/env.bak .env; docker compose up -d api >/dev/null 2>&1; echo; echo 'Tunnels fermés, CORS_ORIGINS restauré.'" EXIT INT TERM; \
	cd frontend && NEXT_PUBLIC_API_BASE_URL=$$API_URL pnpm dev

test-e2e: ## Parcours end-to-end et accessibilité (API et frontend doivent tourner)
	cd frontend && pnpm exec playwright test

lint-frontend: ## ESLint + vérification TypeScript
	cd frontend && pnpm lint && pnpm exec tsc --noEmit

bench: ## Benchmark du générateur (20 seeds, budget 20 s) -> backend/benchmarks/latest.json
	$(BACKEND_RUN) "pip install -q -r requirements.txt && python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json"

# Lexique curé s'il a été exporté, comme l'API ; sinon le DELA complet
LOAD_LEXICON := $(if $(wildcard data/lexicon/build/lexique_cure.csv),-e LEXICON_PATH=/lexicon/lexique_cure.csv,)

bench-load: ## Profil de charge : RAM, CPU par génération, concurrence (2 CPU, 2 Go, comme un petit VPS) -> backend/benchmarks/load.json
	docker run --rm --cpus=2 --memory=2g -v "$(CURDIR)/backend":/app -v "$(CURDIR)/data/lexicon/build":/lexicon:ro \
		$(LOAD_LEXICON) -w /app -e PYTHONDONTWRITEBYTECODE=1 $(PY_IMAGE) sh -c \
		"pip install -q -r requirements.txt && python benchmarks/load_profile.py --output benchmarks/load.json"

db-backup: ## Sauvegarde PostgreSQL dans backups/ (chiffrée si BACKUP_AGE_RECIPIENT, rotation à 30 jours)
	tools/db/backup.sh

db-restore-check: ## Restaure FILE=backups/... dans une base jetable et compte les lignes (la base en service n'est pas touchée)
	@test -n "$(FILE)" || (echo "Usage : make db-restore-check FILE=backups/terminator-....dump" && exit 1)
	tools/db/restore-check.sh "$(FILE)"
