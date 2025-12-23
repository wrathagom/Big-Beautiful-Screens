#!/bin/bash

# Test API quota by sending N updates to a screen
# Usage: ./test_quota.sh <api_key> <screen_id> <count> [base_url]

API_KEY="${1:?Usage: $0 <api_key> <screen_id> <count> [base_url]}"
SCREEN_ID="${2:?Usage: $0 <api_key> <screen_id> <count> [base_url]}"
COUNT="${3:?Usage: $0 <api_key> <screen_id> <count> [base_url]}"
BASE_URL="${4:-http://localhost:8000}"

echo "Sending $COUNT updates to screen $SCREEN_ID..."
echo "Base URL: $BASE_URL"
echo ""

for i in $(seq 1 $COUNT); do
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "$BASE_URL/api/v1/screens/$SCREEN_ID/message" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{\"content\": [\"Test update #$i\"]}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "429" ]; then
        echo "[$i] QUOTA EXCEEDED (429)"
        echo "$body" | head -c 200
        echo ""
        break
    elif [ "$http_code" = "200" ]; then
        echo "[$i] OK (200)"
    else
        echo "[$i] ERROR ($http_code): $body"
    fi
done

echo ""
echo "Done."
