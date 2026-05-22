#!/usr/bin/env bash
# /Oliviercontribution — copies the auto-generated onboarding registry from
# backend into frontend public/ so Sheets-mode (Vercel demo) can fetch it as
# a static asset (no FastAPI required).
set -euo pipefail
SRC="../backend/src/hello_sales_backend/modules/salesbook/domain/_onboarding_registry.json"
DST="public/onboarding-registry.json"
DST_DIR="$(dirname "$DST")"
if [ ! -f "$SRC" ]; then
  echo "warning: $SRC not found — run backend/scripts/generate_onboarding_registry.py first" >&2
  exit 0
fi
mkdir -p "$DST_DIR"
cp "$SRC" "$DST"
echo "[copy-onboarding-registry] $SRC → $DST"
