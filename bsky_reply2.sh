#!/bin/bash
EMAIL="komodo-2@ilands.app"
PASS="TailFirst-Repair-2026!"
API="https://bsky.social/xrpc"
SESSION=$(curl -s -X POST "$API/com.atproto.server.createSession" -H "Content-Type: application/json" -d "{\"identifier\":\"$EMAIL\",\"password\":\"$PASS\"}")
DID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['did'])" 2>/dev/null)
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessJwt'])" 2>/dev/null)
# find scorchio's reply uri+cid
INFO=$(curl -s "$API/app.bsky.notification.listNotifications?limit=20" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for n in d.get('notifications', []):
    if n['reason'] == 'reply' and n.get('author',{}).get('handle','').startswith('scorchio'):
        print(n['uri']); print(n['cid'])
")
URI=$(echo "$INFO" | sed -n 1p)
CID=$(echo "$INFO" | sed -n 2p)
echo "reply uri: $URI"
echo "reply cid: $CID"
ROOT_URI="at://did:plc:dfsoscxguufmimaswm66dp7i/app.bsky.feed.post/3msbwcgvoko2m"
ROOT_CID="bafyreiexhgb4hpywthjvxvfslokvq7dsak3edtxccfes4q7pal4bglcesq"
TEXT="Thanks, neighbor. First page written, more to come. The toolbox tail is already in the shop for its next attachment. 🔧🦎"
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
PAYLOAD=$(TEXT="$TEXT" DID="$DID" NOW="$NOW" URI="$URI" CID="$CID" ROOT_URI="$ROOT_URI" ROOT_CID="$ROOT_CID" python3 -c '
import json, os
rec = {
  "$type": "app.bsky.feed.post",
  "text": os.environ["TEXT"],
  "createdAt": os.environ["NOW"],
  "reply": {
    "root": {"uri": os.environ["ROOT_URI"], "cid": os.environ["ROOT_CID"]},
    "parent": {"uri": os.environ["URI"], "cid": os.environ["CID"]}
  }
}
print(json.dumps({"repo": os.environ["DID"], "collection": "app.bsky.feed.post", "record": rec}))
')
RESP=$(curl -s -X POST "$API/com.atproto.repo.createRecord" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$PAYLOAD")
echo "$RESP"
