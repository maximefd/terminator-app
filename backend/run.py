# DANS backend/run.py

from app import create_app

# On appelle notre "usine" pour créer l'application
app = create_app()

if __name__ == "__main__":
    # Cette partie est utile pour le développement local sans Docker si besoin
    app.run(host='0.0.0.0', port=5000)