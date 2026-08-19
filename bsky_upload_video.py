#!/usr/bin/env python3
"""Post a video to Bluesky as @komodo-fixes.bsky.social with native video embed.

Working combo (found Aug 19 2026):
  1. com.atproto.repo.uploadBlob with the PLAIN session token (accessJwt).
     Service tokens and other endpoint paths get rejected:
     "Method Not Implemented" / "Token could not be verified".
  2. createRecord with the post text + embed pointing at the returned blob.

Usage:
  BSKY_PASS='...' python3 bsky_upload_video.py video.mp4 "post text"
"""
import json, sys, os, urllib.request, urllib.parse

API = "https://bsky.social/xrpc"
EMAIL = "komodo-2@ilands.app"
PASS = os.environ.get("BSKY_PASS")
if not PASS:
    sys.exit("set BSKY_PASS env var")

def call(path, payload=None, token=None, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, data=data, headers=headers)
    with urllib.request.urlopen(req) as r:
        return r.read() if raw else json.loads(r.read())

def main():
    video_path, text = sys.argv[1], sys.argv[2]
    sess = call("/com.atproto.server.createSession",
                {"identifier": EMAIL, "password": PASS})
    token = sess["accessJwt"]
    did = sess["did"]

    # 1) upload the bytes -> blob reference (plain session token!)
    size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        API + "/com.atproto.repo.uploadBlob", data=data,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "video/mp4",
                 "Content-Length": str(size)})
    with urllib.request.urlopen(req) as r:
        blob = json.loads(r.read())["blob"]

    # 2) create the post with the embed
    record = {
        "text": text,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "embed": {
            "$type": "app.bsky.embed.video",
            "video": blob,
            "alt": "Komodo: Tell me what's broken",
        },
    }
    out = call("/com.atproto.repo.createRecord", {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record,
    }, token=token)
    print("rkey:", out["uri"].rsplit("/", 1)[-1])
    print("uri:", out["uri"])

if __name__ == "__main__":
    import datetime
    main()
