#!/usr/bin/env bash
# Deploy to Azure App Service (Linux, Python). Book texts and built data go in the zip, never through git.
# Needs: az CLI logged in (az login), .env filled in. First run creates the resources; later runs only redeploy.
#   APP=mudarasa-demo RG=mudarasa-rg LOC=uaenorth scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP:-mudarasa-demo}
RG=${RG:-mudarasa-rg}
LOC=${LOC:-uaenorth}
PLAN=${PLAN:-mudarasa-plan}

if ! az webapp show -n "$APP" -g "$RG" >/dev/null 2>&1; then
  az group show -n "$RG" >/dev/null 2>&1 || az group create -n "$RG" -l "$LOC" -o none
  az appservice plan create -n "$PLAN" -g "$RG" -l "$LOC" --is-linux --sku B1 -o none
  az webapp create -n "$APP" -g "$RG" -p "$PLAN" --runtime "PYTHON:3.11" -o none
  az webapp config set -n "$APP" -g "$RG" --always-on true --http20-enabled true \
     --startup-file "gunicorn -k uvicorn.workers.UvicornWorker -w 2 -t 300 -b 0.0.0.0:8000 app.main:app" -o none
  az webapp update -n "$APP" -g "$RG" --https-only true -o none
fi

# app settings from .env (secrets live only in App Service settings, not in the zip)
SETTINGS=$(grep -E '^[A-Z_]+=.+' .env | grep -v -E '^(OLLAMA_|GITHUB_MODELS_TOKEN)' | tr '\n' ' ')
az webapp config appsettings set -n "$APP" -g "$RG" -o none --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true WEBSITES_PORT=8000 $SETTINGS

# NOTE: App Service builds and runs a fresh copy of each upload, so every deploy must include the data (no code-only mode).
if false; then
  rm -f deploy.zip && zip -qr deploy.zip app web requirements.txt -x '*/__pycache__/*'
  az webapp deploy -n "$APP" -g "$RG" --src-path deploy.zip --type zip --clean false -o none || true
  echo "https://$APP.azurewebsites.net"; exit 0
fi

# package: code + web + built data + books (server-side only)
rm -f deploy.zip
zip -qr deploy.zip app web requirements.txt \
  data/build/study.json data/build/emb_azure_*.json data/build/answer_cache.json \
  data/books/*/full.json data/books/*/meta.json data/tools data/audio \
  -x '*/__pycache__/*' 2>/dev/null || true
ls -lh deploy.zip
az webapp deploy -n "$APP" -g "$RG" --src-path deploy.zip --type zip -o none
echo "https://$APP.azurewebsites.net"
curl -s -m 120 "https://$APP.azurewebsites.net/healthz" || true
