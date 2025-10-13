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

# Étape 5: La commande à exécuter quand le conteneur démarre (MODIFIÉE)
CMD ["python", "run.py"]