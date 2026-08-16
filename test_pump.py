#!/usr/bin/env python3
"""Test 5: which activity keeps screencast frames flowing? Phase A: evaluate pump.
Phase B: pure sleep. Phase C: beginFrame pump."""
import sys, os, time, base64, hashlib
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
W, H = 1280, 720
count = 0
hashes = []
start = time.time()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    cdp = page.context.new_cdp_session(page)

    def on_frame(params):
        global count
        count += 1
        data = base64.b64decode(params["data"])
        if count % 10 == 0:
            hashes.append(hashlib.md5(data).hexdigest()[:8])
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80, "maxWidth": W, "maxHeight": H})
    page.goto(URL, wait_until="load", timeout=60000)
    page.click("button.btn", timeout=5000)
    time.sleep(1.0)

    def phase(name, secs, mode):
        global count
        before = count
        t0 = time.time()
        while time.time() - t0 < secs:
            if mode == "eval":
                page.evaluate("void 0")
            elif mode == "beginframe":
                try:
                    cdp.send("HeadlessExperimental.beginFrame", {})
                except Exception:
                    pass
            time.sleep(0.1)
        print(f"{name}: +{count - before} frames in {secs}s", flush=True)

    phase("A eval-pump", 5, "eval")
    phase("B sleep-only", 5, "sleep")
    phase("C beginframe-pump", 5, "beginframe")
    cdp.send("Page.stopScreencast")
    browser.close()
    print("unique sample hashes:", len(set(hashes)), "of", len(hashes), flush=True)
