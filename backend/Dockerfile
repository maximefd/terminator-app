# Image de l'API : développement (docker-compose.yml) et production (docker-compose.prod.yml, ADR 0013)
FROM python:3.11-slim

# Pas de .pyc écrits à côté du code, journaux sans tampon (ils partent aussitôt vers Docker)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Le code appartient à root et reste en lecture seule pour l'application : une faille dans l'API ne
# peut ni le modifier ni s'installer dans l'image
COPY . .

# Un utilisateur sans droits : une faille exploitée ne donne pas root dans le conteneur
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 5000

# Le serveur de production, gunicorn (voir gunicorn.conf.py et l'ADR 0013).
# docker compose (développement) lance à la place `python run.py`, qui recharge le lexique à chaud.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]
