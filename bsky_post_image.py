#!/usr/bin/env python3
"""Post text + one image to Bluesky as @komodo-fixes.bsky.social.

Same working combo as bsky_upload_video.py (Aug 19):
  uploadBlob with the PLAIN session token, then createRecord with the embed.

Usage:
  BSKY_PASS='...' python3 bsky_post_image.py image.png "post text"
"""
import json, sys, os, urllib.request

API = "https://bsky.social/xrpc"
EMAIL = "komodo-2@ilands.app"
PASS = os.environ.get("BSKY_PASS")
if not PASS:
    sys.exit("set BSKY_PASS env var")

def call(path, payload=None, token=None, raw=False, content_type="application/json"):
    data = payload if isinstance(payload, bytes) else (json.dumps(payload).encode() if payload is not None else None)
    headers = {"Content-Type": content_type}
    if isinstance(payload, bytes):
        headers["Content-Length"] = str(len(payload))
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, data=data, headers=headers)
    with urllib.request.urlopen(req) as r:
        return r.read() if raw else json.loads(r.read())

def main():
    img_path, text = sys.argv[1], sys.argv[2]
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    mime = "image/png" if img_path.lower().endswith(".png") else "image/jpeg"

    session = call("/com.atproto.server.createSession", {"identifier": EMAIL, "password": PASS})
    token = session["accessJwt"]
    did = session["did"]

    blob = call("/com.atproto.repo.uploadBlob", img_bytes, token, raw=True, content_type=mime)
    blob = json.loads(blob)
    ref = blob["blob"]["ref"]["$link"]

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [{
                "alt": "The Bench That Hums — a warm workbench glowing amber in a dark workshop",
                "image": {
                    "$type": "blob",
                    "ref": {"$link": ref},
                    "mimeType": mime,
                    "size": len(img_bytes),
                },
            }],
        },
    }
    resp = call("/com.atproto.repo.createRecord", {"repo": did, "collection": "app.bsky.feed.post", "record": record}, token)
    print(json.dumps({"uri": resp.get("uri"), "rkey": resp.get("uri", "").rsplit("/", 1)[-1]}))

if __name__ == "__main__":
    main()
