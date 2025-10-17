from app import create_app

# On appelle notre "usine" pour créer l'application
app = create_app()

if __name__ == "__main__":
    # MODIFICATION ICI : On désactive le rechargement automatique
    # C'est la correction qui va stabiliser l'application.
    # Le mode debug reste actif pour avoir des messages d'erreur clairs.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)