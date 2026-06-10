#!/usr/bin/env bash
# /Oliviercontribution — bootstraps the onboarding registry into frontend public/.
#
# The demo onboarding flow uses a *curated* registry (the 80-question / 2-phase
# set Olivier maintains in Google Sheets) which differs from the backend's
# 3-phase / 114-question production model. To keep the demo stable, this script
# only copies the backend registry when public/onboarding-registry.json is
# ABSENT (first-time bootstrap). If the curated demo file already exists, we
# leave it untouched so dev/build don't clobber it.
#
# To force-resync from the backend, delete public/onboarding-registry.json
# first, then run `npm run copy-registry`.
set -euo pipefail
SRC="../backend/src/hello_sales_backend/modules/salesbook/domain/_onboarding_registry.json"
DST="public/onboarding-registry.json"
DST_DIR="$(dirname "$DST")"

if [ -f "$DST" ]; then
  echo "[copy-onboarding-registry] $DST already present — keeping curated demo registry (skip)."
  exit 0
fi
if [ ! -f "$SRC" ]; then
  echo "warning: $SRC not found — run backend/scripts/generate_onboarding_registry.py first" >&2
  exit 0
fi
mkdir -p "$DST_DIR"
cp "$SRC" "$DST"
echo "[copy-onboarding-registry] bootstrapped $DST from backend"
