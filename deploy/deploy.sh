#!/usr/bin/env bash
# Deploy: lädt den committeten UND gepushten Stand von public/ per FTPS in den Docroot.
# Ziel: FTP-Root = Domain-Ordner, Docroot = httpdocs/, SQLite liegt außerhalb in private/.
# Nutzung: deploy/deploy.sh   (Zugangsdaten in .env: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS, SITE_URL, ADMIN_TOKEN, ADMIN_MAIL)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
set -a; . ./.env; set +a

# Regel: nur deployen, was auf GitHub liegt
git fetch -q origin
if [[ -n "$(git status --porcelain -- public)" ]]; then echo "Abbruch: uncommittete Änderungen in public/"; exit 1; fi
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse '@{u}')" ]]; then echo "Abbruch: HEAD ist nicht gepusht"; exit 1; fi

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git archive HEAD public | tar -x -C "$TMP"
cat > "$TMP/public/api/config.php" <<PHP
<?php
return ['db_path' => dirname(__DIR__, 2) . '/private/bow.sqlite', 'admin_token' => '$ADMIN_TOKEN', 'admin_mail' => '${ADMIN_MAIL:-}', 'mail_from' => '${MAIL_FROM:-}'];
PHP

# Ordner für die SQLite-Datenbank außerhalb des Docroots
: > "$TMP/.keep"
curl -sS --max-time 60 --ssl-reqd -k --ftp-create-dirs --user "$DEPLOY_USER:$DEPLOY_PASS" -T "$TMP/.keep" "ftp://$DEPLOY_HOST/private/.keep"

cd "$TMP/public"
n=0
while IFS= read -r -d '' f; do
  f="${f#./}"
  curl -sS --max-time 120 --retry 2 --ssl-reqd -k --ftp-create-dirs --user "$DEPLOY_USER:$DEPLOY_PASS" \
    -T "$f" "ftp://$DEPLOY_HOST/httpdocs/$f"
  n=$((n + 1))
done < <(find . -type f ! -name config.sample.php -print0)
echo "hochgeladen: $n Dateien ($(git -C "$OLDPWD" rev-parse --short HEAD))"

check() { printf '%-28s %s\n' "$1" "$(curl -sk -o /dev/null -w '%{http_code}' "$SITE_URL/$1")"; }
check ""
check "data/places.json"
check "api/api.php?a=captcha"
check "api/lib.php"            # erwartet 403
check "api/config.php"         # erwartet 403
check "api/data/.htaccess"     # erwartet 403
