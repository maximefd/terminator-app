import os

from app import create_app

# On appelle notre "usine" pour créer l'application
app = create_app()

if __name__ == "__main__":
    # Le mode debug n'est activé que si FLASK_DEBUG=1 (docker compose en dev).
    # Jamais en production : le débogueur Werkzeug permet d'exécuter du code à distance.
    debug = os.environ.get("FLASK_DEBUG") == "1"
    port = int(os.environ.get("PORT", 5000))
    # Rechargement automatique désactivé : il chargerait le dictionnaire deux fois.
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
