#!/usr/bin/env bash
set -euo pipefail

# Simple curl-based tests for the /api/v1/test/triage endpoint.
# Usage:
#   ./backend/tests/curl/test_triage.sh [SESSION_ID]
#
# If SESSION_ID is not provided, seeds test data automatically.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"

# Seed test data if SESSION_ID not provided
if [[ -z "${1:-}" ]]; then
  echo "Seeding test data..."
  eval "$(python "${SCRIPT_DIR}/seed_test_data.py" 2>/dev/null | grep '^export ')"
else
  SESSION_ID="${1}"
fi

echo "== Using BASE_URL=${BASE_URL} =="
echo "== Using SESSION_ID=${SESSION_ID} =="

echo
echo "--- Test 1: Skill practice → should ASSESS ---"

curl -sS -X POST "${BASE_URL}/api/v1/test/triage" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "session_id": "${SESSION_ID}",
  "user_response": "So, um, I think we should definitely move forward with this proposal because the data clearly shows a 20% improvement in efficiency.",
  "context": [
    {
      "role": "assistant",
      "content": "Practice pitching me on your project proposal. Focus on being clear and persuasive."
    },
    {
      "role": "user",
      "content": "Okay, let me try..."
    }
  ]
}
EOF

echo
echo
echo "--- Test 2: General chatter → should SKIP ---"

curl -sS -X POST "${BASE_URL}/api/v1/test/triage" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "session_id": "${SESSION_ID}",
  "user_response": "What topics can you help me practice?",
  "context": []
}
EOF

echo
