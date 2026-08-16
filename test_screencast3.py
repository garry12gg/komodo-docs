#!/usr/bin/env python3
"""Test 3: captureScreenshot loop — do frames flow and does animation progress?"""
import sys, os, time, hashlib
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
W, H = 1280, 720
os.makedirs(OUT, exist_ok=True)
start = time.time()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    page.goto(URL, wait_until="load", timeout=60000)
    time.sleep(2)
    page.click("button.btn", timeout=5000)
    time.sleep(1)

    hashes = []
    for i in range(30):
        t0 = time.time()
        page.screenshot(path=f"{OUT}/s{i:04d}.png")
        with open(f"{OUT}/s{i:04d}.png", "rb") as fh:
            hashes.append(hashlib.md5(fh.read()).hexdigest()[:8])
        dt = time.time() - t0
        # pace to ~10fps
        if dt < 0.1:
            time.sleep(0.1 - dt)
    unique = len(set(hashes))
    print(f"30 shots, {unique} unique pixels, elapsed={time.time()-start:.1f}s")
    print("hash run:", hashes[:15])
    browser.close()
