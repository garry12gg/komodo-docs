#!/usr/bin/env python3
"""Capture the ending state: solve all 5 correctly, then watch the ending for ~10s, screenshots."""
import sys, time
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
SOLUTION = ["bridge", "lantern", "key", "ladder", "flame"]

def visible_buttons(page):
    return page.evaluate("""
        Array.from(document.querySelectorAll('button')).map((e,i)=>({i, txt:(e.innerText||'').trim(), vis:!!(e.offsetWidth||e.offsetHeight)})).filter(b=>b.vis)
    """)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(1.5)
    page.click("button.btn", timeout=5000)
    time.sleep(2.5)

    for i, answer in enumerate(SOLUTION):
        btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        target = next((b for b in btns if b["txt"].lower() == answer), None)
        if target is None:
            print(f"step {i}: {answer} not found in {[b['txt'] for b in btns]}")
            break
        # settle first so text baseline is stable
        time.sleep(0.8)
        page.evaluate(f"document.querySelectorAll('button')[{target['i']}].click()")
        print(f"solved {i+1}/5 with {answer}")
        time.sleep(2.2)

    # ending: watch for ~12s
    for k in range(6):
        time.sleep(2)
        page.screenshot(path=f"/tmp/end_{k}.png")
        txt = page.evaluate("document.body.innerText")
        print(f"end {k}: len={len(txt)} | tail: {txt[-220:]!r}")
    browser.close()
