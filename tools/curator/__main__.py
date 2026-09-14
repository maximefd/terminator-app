import os
import sys

from tools.lexicon.cli import DEFAULT_DB, DEFAULT_DECISIONS

from .app import create_app


def main() -> None:
    try:
        app = create_app(DEFAULT_DB, DEFAULT_DECISIONS, os.environ.get("CURATOR_PIN", ""),
                         os.environ.get("CURATOR_SECRET_KEY") or None)
    except (ValueError, FileNotFoundError) as error:
        sys.exit(f"Impossible de démarrer le curateur : {error}")
    port = int(os.environ.get("CURATOR_PORT", 8765))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


main()
