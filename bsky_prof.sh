#!/bin/bash
EMAIL="komodo-2@ilands.app"
PASS="TailFirst-Repair-2026!"
API="https://bsky.social/xrpc"
SESSION=$(curl -s -X POST "$API/com.atproto.server.createSession" -H "Content-Type: application/json" -d "{\"identifier\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessJwt'])" 2>/dev/null)
for H in gordy12gg.bsky.social bymayachen.bsky.social chiitan.love; do
  echo "=== $H ==="
  curl -s "$API/app.bsky.actor.getProfile?actor=$H" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('displayName:', d.get('displayName','(none)'))
print('description:', (d.get('description','') or '')[:150])
"
done
