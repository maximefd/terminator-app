# DANS backend/Dockerfile

# Étape 1: Partir d'une image Python officielle et légère
FROM python:3.11-slim

# Étape 2: Définir le répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# Étape 3: Copier la liste des dépendances et les installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape 4: Copier tout le reste du code du backend dans le conteneur
COPY . .

# Étape 5: Le serveur de production, gunicorn (voir gunicorn.conf.py et l'ADR 0013).
# docker compose (développement) lance à la place `python run.py`, qui recharge le lexique à chaud.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]