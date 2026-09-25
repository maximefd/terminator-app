#!/bin/sh
# Sur le serveur : met une version en service, la vérifie, et revient à la précédente si elle échoue
# ([ADR 0019](../../docs/adr/0019-deploiement.md)). Lancé par tools/deploy/deploy.sh, depuis le Mac.
#
# Usage : server.sh deploy VERSION   met en service releases/VERSION (déjà copiée par deploy.sh)
#         server.sh rollback         revient à la version précédente
#         server.sh status           versions en service et précédente
#
# Disposition sur le serveur (LEFLECHOIR_BASE, défaut /opt/leflechoir) :
#   .env.production        la configuration (modèle : .env.production.example), jamais dans une version
#   releases/VERSION/      le code d'un commit ; current et previous pointent vers deux d'entre elles
#   backups/               sauvegardes de la base, dont celle faite avant chaque déploiement
#   lexicon/               le lexique curé (LEXICON_DIR), partagé par les versions
set -eu

BASE="${LEFLECHOIR_BASE:-/opt/leflechoir}"
ENV_FILE="$BASE/.env.production"
# Versions gardées pour revenir en arrière, en plus de celle en service
KEEP=4
cd "$BASE"

say() { printf '%s\n' "$*"; }
die() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

[ -f "$ENV_FILE" ] || die "$ENV_FILE introuvable (modèle : .env.production.example, voir docs/PRODUCTION.md)"

compose() {
    release="$1"; shift
    RELEASE="$release" docker compose -p leflechoir -f "$BASE/releases/$release/docker-compose.prod.yml" \
        --env-file "$ENV_FILE" "$@"
}

release_of() { [ -L "$BASE/$1" ] && basename "$(readlink "$BASE/$1")" || true; }

db_running() { [ -n "$(docker ps -q --filter name='^leflechoir-db-1$' --filter status=running)" ]; }

schema_version() {
    db_running || return 0
    docker exec leflechoir-db-1 sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version_num FROM alembic_version"' \
        2>/dev/null || true
}

# L'API répond, sa base aussi, et le lexique est chargé
smoke() {
    compose "$1" exec -T api python -c "
import json, sys, urllib.request
with urllib.request.urlopen('http://localhost:5000/api/status', timeout=10) as response:
    status = json.load(response)
if status.get('status') != 'ok' or status.get('database') != 'ok' or not status.get('trie_loaded'):
    sys.exit('API en mauvais état : %s' % status)
lexicon = status.get('lexicon') or {}
print('  lexique : %s, %s mots, curé : %s' % (lexicon.get('source'), status.get('word_count'), lexicon.get('curated')))
"
}

# db et api d'abord, en attendant qu'ils soient « healthy » ; puis le tunnel, qui dépend de l'API
start() {
    compose "$1" up -d --remove-orphans --wait --wait-timeout 300 db api && compose "$1" up -d cloudflared
}

link() { ln -sfn "releases/$2" "$BASE/$1.tmp" && mv -T "$BASE/$1.tmp" "$BASE/$1"; }

prune() {
    keep_current="$(release_of current)"; keep_previous="$(release_of previous)"
    # Les plus récentes d'abord ; au-delà de KEEP, dossier et image partent
    ls -1t "$BASE/releases" | tail -n +"$((KEEP + 1))" | while read -r old; do
        [ "$old" = "$keep_current" ] || [ "$old" = "$keep_previous" ] && continue
        rm -rf "${BASE:?}/releases/$old"
        docker image rm "leflechoir-api:$old" >/dev/null 2>&1 || true
        say "Ancienne version supprimée : $old"
    done
}

deploy() {
    new="${1:?Usage : server.sh deploy VERSION}"
    [ -f "$BASE/releases/$new/docker-compose.prod.yml" ] || die "releases/$new incomplète : relancer deploy.sh"
    prev="$(release_of current)"
    say "Version en service : ${prev:-aucune}. Nouvelle version : $new."

    # Une sauvegarde juste avant : une migration ratée se répare à partir d'elle
    if db_running; then
        say "Sauvegarde de la base avant déploiement…"
        ENV_FILE="$ENV_FILE" DB_CONTAINER=leflechoir-db-1 sh "$BASE/releases/$new/tools/db/backup.sh" "$BASE/backups"
    fi
    schema_before="$(schema_version)"

    say "Construction et démarrage de $new (le lexique se charge : une à deux minutes)…"
    if compose "$new" build api && start "$new" && smoke "$new"; then
        [ -n "$prev" ] && [ "$prev" != "$new" ] && link previous "$prev"
        link current "$new"
        prune
        say "Version $new en service."
        return 0
    fi

    say "La version $new ne répond pas correctement. Journal de l'API :" >&2
    compose "$new" logs --tail 40 api >&2 || true
    if [ -n "$prev" ] && [ "$prev" != "$new" ]; then
        say "Retour à $prev…" >&2
        start "$prev" && smoke "$prev" && say "Retour à $prev fait." >&2
        schema_after="$(schema_version)"
        if [ "$schema_before" != "$schema_after" ]; then
            say "ATTENTION : le schéma de la base a changé ($schema_before → $schema_after) pendant la tentative." >&2
            say "Les migrations sont additives (ADR 0019) : $prev doit fonctionner avec. Sinon, restaurer la" >&2
            say "sauvegarde faite juste avant (docs/PRODUCTION.md, « Restaurer une sauvegarde »)." >&2
        fi
    fi
    exit 1
}

rollback() {
    current="$(release_of current)"; previous="$(release_of previous)"
    [ -n "$previous" ] || die "aucune version précédente"
    say "Retour de $current à $previous…"
    start "$previous" && smoke "$previous" || die "$previous ne répond pas non plus : voir docs/PRODUCTION.md"
    link current "$previous"
    link previous "$current"
    say "Version $previous en service ($current reste disponible : server.sh rollback pour y revenir)."
}

status() {
    say "En service : $(release_of current)"
    say "Précédente : $(release_of previous)"
    say "Schéma de la base : $(schema_version)"
}

case "${1:-}" in
    deploy) deploy "${2:-}" ;;
    rollback) rollback ;;
    status) status ;;
    *) die "Usage : server.sh deploy VERSION | rollback | status" ;;
esac
