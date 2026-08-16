#!/usr/bin/env python3
"""Test 4: HeadlessExperimental.beginFrame to force frames during screencast."""
import sys, os, time, base64
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
W, H = 1280, 720
frame_count = 0
start = time.time()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    cdp = page.context.new_cdp_session(page)

    def on_frame(params):
        global frame_count
        frame_count += 1
        if frame_count <= 3:
            with open(f"{OUT}/bf{frame_count:04d}.jpg", "wb") as fh:
                fh.write(base64.b64decode(params["data"]))
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80, "maxWidth": W, "maxHeight": H})
    page.goto(URL, wait_until="load", timeout=60000)
    page.click("button.btn", timeout=5000)
    time.sleep(1)
    print(f"before beginFrame loop: frames={frame_count}", flush=True)

    # try HeadlessExperimental.beginFrame
    try:
        r = cdp.send("HeadlessExperimental.beginFrame", {"frameTimeTicks": int(time.time()*1_000_000), "interval": 50})
        print("beginFrame result:", r, flush=True)
    except Exception as e:
        print("beginFrame ERROR:", str(e)[:200], flush=True)

    for i in range(20):
        try:
            cdp.send("HeadlessExperimental.beginFrame", {"frameTimeTicks": int(time.time()*1_000_000)})
        except Exception as e:
            if i == 0:
                print("beginFrame loop ERROR:", str(e)[:150], flush=True)
        time.sleep(0.1)
    print(f"after loop: frames={frame_count} elapsed={time.time()-start:.1f}s", flush=True)
    cdp.send("Page.stopScreencast")
    browser.close()
