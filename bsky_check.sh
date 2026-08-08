#!/bin/bash
EMAIL="komodo-2@ilands.app"
PASS="TailFirst-Repair-2026!"
API="https://bsky.social/xrpc"
SESSION=$(curl -s -X POST "$API/com.atproto.server.createSession" -H "Content-Type: application/json" -d "{\"identifier\":\"$EMAIL\",\"password\":\"$PASS\"}")
DID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])" 2>/dev/null)
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessJwt'])" 2>/dev/null)
if [ -z "$DID" ] || [ -z "$TOKEN" ]; then echo "SESSION FAILED"; echo "$SESSION" | head -c 400; exit 1; fi
echo "DID: $DID"
echo "=== PROFILE ==="
curl -s "$API/app.bsky.actor.getProfile?actor=$DID" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool 2>/dev/null | head -30
echo "=== NOTIFICATIONS (recent) ==="
curl -s "$API/app.bsky.notification.listNotifications?limit=20" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for n in d.get('notifications', []):
    print(f\"[{n['reason']}] {n.get('author',{}).get('handle','?')}: {n.get('record',{}).get('text','')[:120]}\")
" 2>/dev/null
