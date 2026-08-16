#!/usr/bin/env python3
"""Minimal screencast test."""
import sys, os, time, base64
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
W, H = 1280, 720
os.makedirs(OUT, exist_ok=True)

frame_count = 0
next_slot = 0.0
start = time.time()

with sync_playwright() as p:
    print("launching...", flush=True)
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    cdp = page.context.new_cdp_session(page)

    def on_frame(params):
        global frame_count, next_slot
        ts = params.get("metadata", {}).get("timestamp", time.time()*1000)/1000.0
        if ts >= next_slot:
            next_slot = ts + 1.0/15.0
            frame_count += 1
            with open(f"{OUT}/f{frame_count:05d}.jpg", "wb") as fh:
                fh.write(base64.b64decode(params["data"]))
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 82, "maxWidth": W, "maxHeight": H})
    print("screencast started", flush=True)

    print("goto...", flush=True)
    page.goto(URL, wait_until="load", timeout=60000)
    print("goto done", flush=True)

    for i in range(8):
        time.sleep(1.0)
        print(f"t={time.time()-start:.1f}s frames={frame_count}", flush=True)

    cdp.send("Page.stopScreencast")
    browser.close()
    print("done", flush=True)
