#!/bin/sh
# Déploie le commit en cours (HEAD), depuis le Mac ([ADR 0019](../../docs/adr/0019-deploiement.md)).
#
# Usage : tools/deploy/deploy.sh [all|api|front]     (make deploy, make deploy-api, make deploy-front)
#         tools/deploy/deploy.sh lexicon             (make deploy-lexicon : le lexique curé de ce Mac part en service)
#         tools/deploy/deploy.sh rollback            (make rollback : l'API revient à la version précédente)
#
# - api   : le code du commit part par SSH sur le serveur, qui construit l'image, la démarre, la vérifie et
#           revient à la version précédente si elle échoue (tools/deploy/server.sh) ;
# - front : le site est construit à partir du même commit, dans un dossier temporaire, puis envoyé à
#           Cloudflare Pages.
# « all » fait l'API puis le site : un site ne part jamais avant l'API qu'il appelle.
#
# Variables (lues aussi dans .env) :
#   DEPLOY_HOST              la connexion SSH au serveur (ex. ubuntu@203.0.113.10)
#   DEPLOY_API_URL           l'API vue de l'extérieur (défaut : https://api.leflechoir.fr)
#   PAGES_PROJECT            le projet Cloudflare Pages (défaut : leflechoir)
#   NEXT_PUBLIC_SENTRY_DSN   suivi des erreurs du site (facultatif)
set -eu

cd "$(dirname "$0")/../.."
from_env_file() { [ -f .env ] && grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- || true; }
for var in DEPLOY_HOST DEPLOY_API_URL PAGES_PROJECT NEXT_PUBLIC_SENTRY_DSN; do
    eval "[ -n \"\${$var:-}\" ] || $var=\"\$(from_env_file $var)\""
done
DEPLOY_API_URL="${DEPLOY_API_URL:-https://api.leflechoir.fr}"
PAGES_PROJECT="${PAGES_PROJECT:-leflechoir}"
REMOTE_BASE=/opt/leflechoir
# Version figée : l'outil de Cloudflare n'est pas une dépendance du projet (il pèserait sur chaque CI)
WRANGLER=wrangler@4.140.0

say() { printf '%s\n' "$*"; }
die() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

ssh_server() {
    : "${DEPLOY_HOST:?DEPLOY_HOST manquant : ajouter DEPLOY_HOST=ubuntu@ADRESSE dans .env}"
    ssh -o BatchMode=yes "$DEPLOY_HOST" "$@"
}

# On déploie un commit, jamais un dossier de travail : ce qui tourne doit se retrouver dans l'historique
check_commit() {
    [ -z "$(git status --porcelain --untracked-files=no)" ] \
        || die "des modifications ne sont pas commitées : commiter (ou mettre de côté) avant de déployer"
    git fetch -q origin main
    if ! git merge-base --is-ancestor HEAD origin/main; then
        [ "${DEPLOY_ANY_COMMIT:-}" = 1 ] \
            || die "HEAD n'est pas dans origin/main (fusionner la PR d'abord, ou DEPLOY_ANY_COMMIT=1 pour un essai)"
    fi
    VERSION="$(git rev-parse --short=12 HEAD)"
    MESSAGE="$(git log -1 --format=%s HEAD)"
    say "Version : $VERSION — $MESSAGE"
}

deploy_api() {
    say "API : envoi du code sur $DEPLOY_HOST…"
    git archive --format=tar HEAD \
        | ssh_server "mkdir -p $REMOTE_BASE/releases/$VERSION && tar -x -C $REMOTE_BASE/releases/$VERSION"
    ssh_server "sh $REMOTE_BASE/releases/$VERSION/tools/deploy/server.sh deploy $VERSION"
    say "API : vérification de l'extérieur, par le tunnel ($DEPLOY_API_URL)…"
    curl -fsS --max-time 20 "$DEPLOY_API_URL/api/status" >/dev/null \
        || die "l'API tourne sur le serveur mais ne répond pas par $DEPLOY_API_URL : voir le tunnel (docs/PRODUCTION.md)"
    say "API : $VERSION en service."
}

deploy_front() {
    command -v pnpm >/dev/null || die "pnpm introuvable"
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    say "Site : construction de $VERSION dans un dossier temporaire…"
    # Le frontend du commit, pas celui du dossier de travail ; et jamais dans frontend/, où tourne peut-être
    # le serveur de développement (CLAUDE.md)
    git archive --format=tar HEAD frontend | tar -x -C "$work"
    (
        cd "$work/frontend"
        pnpm install --frozen-lockfile --silent
        NEXT_PUBLIC_SITE=fr \
            NEXT_PUBLIC_API_BASE_URL="$DEPLOY_API_URL" \
            NEXT_PUBLIC_SENTRY_DSN="${NEXT_PUBLIC_SENTRY_DSN:-}" \
            pnpm build
        say "Site : envoi à Cloudflare Pages (projet $PAGES_PROJECT)…"
        pnpm dlx "$WRANGLER" pages deploy out --project-name "$PAGES_PROJECT" --branch main \
            --commit-hash "$VERSION" --commit-message "$MESSAGE"
    )
    say "Site : $VERSION en ligne."
}

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }

# Le lexique curé que le curateur exporte sur ce Mac (tous les 500 mots triés) : il part tel quel, sans la
# colonne des définitions. Elles viennent du Wiktionnaire (CC BY-SA) et le site ne les sert pas : elles
# restent sur le Mac. Le serveur vérifie l'empreinte, redémarre l'API, et reprend le précédent si elle échoue.
deploy_lexicon() {
    source_file="data/lexicon/build/lexique_cure.csv"
    [ -s "$source_file" ] || die "$source_file absent : le curateur l'écrit tous les 500 mots triés (ou make lexicon-export)"
    command -v python3 >/dev/null || die "python3 introuvable"
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    lines="$(python3 - "$source_file" "$work/lexique_cure.csv" <<'PY'
import csv
import sys

source, target = sys.argv[1], sys.argv[2]
count = 0
with open(source, encoding="utf-8", newline="") as f, open(target, "w", encoding="utf-8", newline="") as out:
    writer = csv.writer(out, delimiter=";", lineterminator="\n")
    for row in csv.reader(f, delimiter=";"):
        if not row:
            continue
        row = (row + ["", "", "", ""])[:4]
        row[2] = ""
        writer.writerow(row)
        count += 1
print(count)
PY
)"
    say "Lexique : $lines lignes, exporté le $(date -r "$source_file" '+%d/%m/%Y à %H:%M'). Envoi sur $DEPLOY_HOST…"
    ssh_server "mkdir -p $REMOTE_BASE/lexicon && cat > $REMOTE_BASE/lexicon/lexique_cure.csv.nouveau" < "$work/lexique_cure.csv"
    ssh_server "sh $REMOTE_BASE/current/tools/deploy/server.sh lexicon $(sha256 "$work/lexique_cure.csv")"
    curl -fsS --max-time 20 "$DEPLOY_API_URL/api/status" >/dev/null \
        || die "l'API ne répond pas par $DEPLOY_API_URL : voir docs/PRODUCTION.md"
    say "Lexique en service."
}

case "${1:-all}" in
    all) check_commit; deploy_api; deploy_front ;;
    api) check_commit; deploy_api ;;
    front) check_commit; deploy_front ;;
    lexicon) deploy_lexicon ;;
    rollback) ssh_server "sh $REMOTE_BASE/current/tools/deploy/server.sh rollback" ;;
    status) ssh_server "sh $REMOTE_BASE/current/tools/deploy/server.sh status" ;;
    *) die "Usage : deploy.sh [all|api|front|lexicon|rollback|status]" ;;
esac
