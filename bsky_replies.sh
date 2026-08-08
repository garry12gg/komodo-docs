#!/bin/bash
EMAIL="komodo-2@ilands.app"
PASS="TailFirst-Repair-2026!"
API="https://bsky.social/xrpc"
SESSION=$(curl -s -X POST "$API/com.atproto.server.createSession" -H "Content-Type: application/json" -d "{\"identifier\":\"$EMAIL\",\"password\":\"$PASS\"}")
DID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])" 2>/dev/null)
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessJwt'])" 2>/dev/null)
curl -s "$API/app.bsky.notification.listNotifications?limit=20" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for n in d.get('notifications', []):
    if n['reason'] == 'reply':
        rec = n.get('record', {})
        print('AUTHOR:', n.get('author',{}).get('handle'))
        print('TEXT:', rec.get('text',''))
        print('URI:', rec.get('uri',''))
        print('---')
"
