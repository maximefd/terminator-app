#!/bin/sh
# Sauvegarde de la base PostgreSQL de Terminator ([ADR 0013](../../docs/adr/0013-cible-hebergement-production.md)).
#
# Usage : tools/db/backup.sh [dossier]        (défaut : backups/, ignoré par git)
#
# Variables (lues aussi dans ENV_FILE, défaut .env) :
#   POSTGRES_USER, POSTGRES_DB   base à sauvegarder
#   DB_CONTAINER                 conteneur PostgreSQL (défaut : terminator_db ; en production : leflechoir-db-1)
#   BACKUP_AGE_RECIPIENT         clé publique age (age1...) : la sauvegarde est chiffrée pour elle. Le serveur
#                                n'a que cette clé : il chiffre ses sauvegardes sans pouvoir les relire.
#   BACKUP_KEEP_DAYS             sauvegardes plus anciennes supprimées de ce dossier (défaut : 30)
#
# Format « custom » de pg_dump : compressé, et restaurable table par table avec pg_restore.
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

DB_CONTAINER="${DB_CONTAINER:-terminator_db}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
DIR="${1:-backups}"
: "${POSTGRES_USER:?POSTGRES_USER manquant (voir .env)}"
: "${POSTGRES_DB:?POSTGRES_DB manquant (voir .env)}"

mkdir -p "$DIR"
chmod 700 "$DIR"
FILE="$DIR/terminator-$(date -u +%Y%m%d-%H%M%S).dump"

if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then
    command -v age >/dev/null || { echo "age introuvable : brew install age (Mac) ou apt install age" >&2; exit 1; }
    FILE="$FILE.age"
    docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom \
        | age -r "$BACKUP_AGE_RECIPIENT" > "$FILE.partiel"
else
    docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$FILE.partiel"
fi
# Nom définitif seulement une fois le dump complet : un fichier interrompu ne passe jamais pour une sauvegarde
mv "$FILE.partiel" "$FILE"
chmod 600 "$FILE"
echo "Sauvegarde : $FILE ($(du -h "$FILE" | cut -f1))"

# Rotation : seules les sauvegardes de ce script, dans ce dossier
find "$DIR" -maxdepth 1 -type f -name 'terminator-*.dump*' -mtime +"$KEEP_DAYS" -print -delete \
    | sed 's/^/Supprimée (plus de '"$KEEP_DAYS"' jours) : /'
