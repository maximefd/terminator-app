#!/bin/sh
# La sauvegarde de la nuit, sur le serveur (#120, ADR 0013) : un dump chiffré de la base, copié hors du serveur
# sur Cloudflare R2, et une trace de la dernière réussite. Lancé chaque nuit par cron (docs/PRODUCTION.md).
#
# Usage : tools/db/backup-offsite.sh
#
# Lit dans .env.production (LEFLECHOIR_BASE, défaut /opt/leflechoir) :
#   BACKUP_AGE_RECIPIENT    clé publique age : obligatoire, rien ne quitte le serveur en clair
#   R2_ENDPOINT             l'adresse S3 du compte (seau en juridiction UE : https://<compte>.eu.r2.cloudflarestorage.com)
#   R2_BUCKET               le seau (ex. leflechoir-sauvegardes)
#   R2_ACCESS_KEY_ID        jeton R2 limité à ce seau (lecture et écriture d'objets)
#   R2_SECRET_ACCESS_KEY
#   BACKUP_PING_URL         facultatif : adresse appelée après une réussite (Healthchecks.io, moniteur de tâche
#                           Sentry…), qui prévient si elle n'est plus appelée
#
# La rotation sur R2 (30 jours) est une règle de cycle de vie du seau : ce script ne supprime rien là-bas.
set -eu

BASE="${LEFLECHOIR_BASE:-/opt/leflechoir}"
ENV_FILE="${ENV_FILE:-$BASE/.env.production}"
BACKUPS="$BASE/backups"
MARKER="$BACKUPS/derniere-sauvegarde"

from_env_file() { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true; }
for var in BACKUP_AGE_RECIPIENT R2_ENDPOINT R2_BUCKET R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_PROVIDER BACKUP_PING_URL; do
    eval "[ -n \"\${$var:-}\" ] || $var=\"\$(from_env_file $var)\""
done

die() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT manquant : une sauvegarde ne quitte le serveur que chiffrée}"
: "${R2_ENDPOINT:?R2_ENDPOINT manquant (voir docs/PRODUCTION.md, « Sauvegardes »)}"
: "${R2_BUCKET:?R2_BUCKET manquant}"
: "${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID manquant}"
: "${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY manquant}"
command -v rclone >/dev/null || die "rclone introuvable : sudo apt install rclone"

# 1. Le dump, chiffré pour la clé publique : le serveur ne peut pas relire ses propres sauvegardes
ENV_FILE="$ENV_FILE" DB_CONTAINER="${DB_CONTAINER:-leflechoir-db-1}" BACKUP_AGE_RECIPIENT="$BACKUP_AGE_RECIPIENT" \
    sh "$(dirname "$0")/backup.sh" "$BACKUPS"
FILE="$(ls -1t "$BACKUPS"/terminator-*.dump.age | head -n 1)"
NAME="$(basename "$FILE")"

# 2. La copie sur R2. Le remote est décrit par l'environnement : aucun fichier de configuration à tenir,
# et le secret reste dans .env.production
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER="${R2_PROVIDER:-Cloudflare}"
export RCLONE_CONFIG_R2_ENDPOINT="$R2_ENDPOINT"
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
# Le jeton ne voit que son seau : ne pas chercher à lister ni créer les seaux du compte
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
# Ne pas relire l'objet après l'envoi : R2 renvoie un identifiant de version, et rclone (1.60, celui
# d'Ubuntu 24.04) relit alors par HEAD ?versionId=…, que R2 refuse (501 NotImplemented). La copie réussissait
# au second essai seulement. L'intégrité reste vérifiée : Content-MD5 contrôlé par R2, puis la taille ci-dessous
export RCLONE_CONFIG_R2_NO_HEAD=true
# Tout ce qui manque là-bas depuis une semaine part aussi : une nuit ratée, les sauvegardes d'avant déploiement
rclone copy --quiet --max-age 7d --include 'terminator-*.dump.age' "$BACKUPS" "r2:$R2_BUCKET"

# 3. Vérifier qu'elle y est, à la bonne taille : une copie non vérifiée n'est pas une copie
local_size="$(wc -c < "$FILE" | tr -d ' ')"
remote_size="$(rclone lsl --quiet "r2:$R2_BUCKET/$NAME" | awk '{print $1}')"
[ "$local_size" = "$remote_size" ] || die "copie sur R2 incomplète : $local_size octets ici, ${remote_size:-rien} là-bas"

# 4. La trace de la dernière réussite, lue par `server.sh status` (et plus tard le poste de pilotage)
printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$NAME" "$local_size" > "$MARKER"
echo "Sauvegarde copiée sur R2 : $NAME ($local_size octets)"

if [ -n "${BACKUP_PING_URL:-}" ]; then
    curl -fsS --max-time 10 --retry 3 "$BACKUP_PING_URL" >/dev/null || echo "Avertissement : $BACKUP_PING_URL injoignable" >&2
fi
