#!/bin/sh
# Vérifie qu'une sauvegarde se restaure, sans toucher à la base en service.
#
# Usage : tools/db/restore-check.sh FICHIER.dump[.age]
#
# La sauvegarde est restaurée dans une base jetable (terminator_verif_restauration) du même serveur
# PostgreSQL, on y compte les lignes des tables principales, puis la base est supprimée. Une sauvegarde
# jamais restaurée n'est pas une sauvegarde : à faire chaque mois (ADR 0013).
#
# Variables : POSTGRES_USER, DB_CONTAINER (défaut : terminator_db), et pour un fichier .age,
# BACKUP_AGE_IDENTITY (fichier de la clé privée age, gardée hors du serveur).
set -eu

cd "$(dirname "$0")/../.."
# Une variable du fichier d'environnement (ENV_FILE, défaut .env ; sur le serveur, .env.production), si
# l'environnement ne la fournit pas déjà. Le fichier n'est pas sourcé : ses valeurs peuvent contenir des
# espaces, comme « 100 per hour »
ENV_FILE="${ENV_FILE:-.env}"
from_env_file() { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true; }
for var in POSTGRES_USER POSTGRES_DB DB_CONTAINER BACKUP_AGE_RECIPIENT BACKUP_AGE_IDENTITY BACKUP_KEEP_DAYS; do
    eval "[ -n \"\${$var:-}\" ] || $var=\"\$(from_env_file $var)\""
done

FILE="${1:?Usage : tools/db/restore-check.sh FICHIER.dump[.age]}"
[ -f "$FILE" ] || { echo "Fichier introuvable : $FILE" >&2; exit 1; }
DB_CONTAINER="${DB_CONTAINER:-terminator_db}"
: "${POSTGRES_USER:?POSTGRES_USER manquant (voir .env)}"
CHECK_DB=terminator_verif_restauration

psql_in() { docker exec -i -e PGOPTIONS=--client-min-messages=warning "$DB_CONTAINER" psql -U "$POSTGRES_USER" -v ON_ERROR_STOP=1 -qAt "$@"; }

dump() {
    case "$FILE" in
        *.age)
            command -v age >/dev/null || { echo "age introuvable : brew install age ou apt install age" >&2; exit 1; }
            : "${BACKUP_AGE_IDENTITY:?BACKUP_AGE_IDENTITY manquant : fichier de la clé privée age}"
            age -d -i "$BACKUP_AGE_IDENTITY" "$FILE" ;;
        *) cat "$FILE" ;;
    esac
}

cleanup() { psql_in -d postgres -c "DROP DATABASE IF EXISTS $CHECK_DB" >/dev/null; }
trap cleanup EXIT

cleanup
psql_in -d postgres -c "CREATE DATABASE $CHECK_DB" >/dev/null
dump | docker exec -i "$DB_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$CHECK_DB" --no-owner --exit-on-error

echo "Restauration réussie ($FILE). Contenu :"
for table in '"user"' dictionary personal_word saved_grid alembic_version; do
    printf '  %-16s %s\n' "$table" "$(psql_in -d "$CHECK_DB" -c "SELECT count(*) FROM $table")"
done
echo "  révision du schéma : $(psql_in -d "$CHECK_DB" -c 'SELECT version_num FROM alembic_version')"
