#!/usr/bin/env bash
set -euo pipefail

# Simple curl-based tests for the /api/v1/test/assess endpoint.
# Usage:
#   ./backend/tests/curl/test_assessment.sh [SESSION_ID SKILL_ID...]
#
# If no args provided, seeds test data automatically.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"

# Seed test data if no args provided
if [[ "$#" -eq 0 ]]; then
  echo "Seeding test data..."
  eval "$(python "${SCRIPT_DIR}/seed_test_data.py" 2>/dev/null | grep '^export ')"
  SKILL_IDS_JSON="[\"${SKILL_ID}\"]"
else
  SESSION_ID="${1}"
  shift

  if [[ "$#" -lt 1 ]]; then
    echo "You must provide at least one SKILL_ID" >&2
    exit 1
  fi

  # Build JSON array of skill IDs from remaining arguments
  SKILL_IDS_JSON="["
  FIRST=1
  for ID in "$@"; do
    if [[ ${FIRST} -eq 1 ]]; then
      FIRST=0
    else
      SKILL_IDS_JSON+=","
    fi
    SKILL_IDS_JSON+="\"${ID}\""
  done
  SKILL_IDS_JSON+="]"
fi

echo "== Using BASE_URL=${BASE_URL} =="
echo "== Using SESSION_ID=${SESSION_ID} =="
echo "== Using SKILL_IDS=${SKILL_IDS_JSON} =="

echo
echo "--- Test: Single assessment call for provided skills ---"

curl -sS -X POST "${BASE_URL}/api/v1/test/assess" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "session_id": "${SESSION_ID}",
  "user_response": "The solution is straightforward. We implement phase one next week, measure results for two weeks, then decide on phase two based on the data.",
  "skill_ids": ${SKILL_IDS_JSON}
}
EOF

echo
