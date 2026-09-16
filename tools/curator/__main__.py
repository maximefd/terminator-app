import os
import sys
from pathlib import Path

from tools.lexicon.cli import DEFAULT_DB, DEFAULT_DECISIONS

from .app import create_app
from .gamification import DEFAULT_DAILY_GOAL


def main() -> None:
    try:
        daily_goal = int(os.environ.get("CURATOR_DAILY_GOAL") or DEFAULT_DAILY_GOAL)
        app = create_app(DEFAULT_DB, DEFAULT_DECISIONS, os.environ.get("CURATOR_PIN", ""),
                         os.environ.get("CURATOR_SECRET_KEY") or None, daily_goal=daily_goal)
    except (ValueError, FileNotFoundError) as error:
        sys.exit(f"Impossible de démarrer le curateur : {error}")
    if not Path(DEFAULT_DB).exists():
        print("Base du lexique absente : seul l'éditeur de layouts est disponible "
              "(make lexicon-build pour trier les mots).", flush=True)
    port = int(os.environ.get("CURATOR_PORT", 8765))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


main()
