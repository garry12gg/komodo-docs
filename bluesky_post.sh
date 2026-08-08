#!/bin/bash
# Post to Bluesky as @komodo-fixes.bsky.social
# Usage: ./bluesky_post.sh "text of post"
set -e
TEXT="$1"
EMAIL="komodo-2@ilands.app"
PASS="TailFirst-Repair-2026!"
API="https://bsky.social/xrpc"

SESSION=$(curl -s -X POST "$API/com.atproto.server.createSession" \
  -H "Content-Type: application/json" \
  -d "{\"identifier\":\"$EMAIL\",\"password\":\"$PASS\"}")
DID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])" 2>/dev/null)
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessJwt'])" 2>/dev/null)
if [ -z "$DID" ] || [ -z "$TOKEN" ]; then
  echo "SESSION FAILED"; echo "$SESSION" | head -c 400; exit 1
fi
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
PAYLOAD=$(TEXT="$TEXT" DID="$DID" NOW="$NOW" python3 -c '
import json, os
d = json.dumps({"$type": "app.bsky.feed.post", "text": os.environ["TEXT"], "createdAt": os.environ["NOW"]})
print(json.dumps({"repo": os.environ["DID"], "collection": "app.bsky.feed.post", "record": json.loads(d)}))
')
RESP=$(curl -s -X POST "$API/com.atproto.repo.createRecord" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "$PAYLOAD")
echo "$RESP"
