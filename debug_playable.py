#!/usr/bin/env python3
"""Debug round: click each button with longer settle, dump full text after each."""
import sys, time, re
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(1.5)
    page.click("button.btn", timeout=5000)
    time.sleep(2.0)

    for attempt in range(4):
        txt = page.evaluate("document.body.innerText")
        print(f"### attempt {attempt} --- text now:")
        print(txt)
        print("---")
        btns = page.evaluate("""
            Array.from(document.querySelectorAll('button')).map((e,i)=>({i, txt:(e.innerText||'').trim(), vis:!!(e.offsetWidth||e.offsetHeight), disabled:e.disabled})).filter(b=>b.vis)
        """)
        print("buttons:", btns)
        if not btns:
            print("no buttons; end?")
            break
        # click the first non-lamp button by its exact index from this fresh query
        target = [b for b in btns if b["txt"].lower() != "light the lamp"][0]
        idx = target["i"]
        page.evaluate(f"document.querySelectorAll('button')[{idx}].click()")
        print(f"clicked button[{idx}] = {target['txt']!r} (via JS)")
        for wait in (0.8, 2.0):
            time.sleep(wait)
            t2 = page.evaluate("document.body.innerText")
            changed = t2 != txt
            print(f"  after {wait}s total-since-click {wait}: changed={changed}")
            if changed:
                print("  NEW TEXT TAIL:", repr(t2[-300:]))
                break
        time.sleep(1.5)
        page.screenshot(path=f"/tmp/dbg_{attempt}.png")
        # if dialogue no longer has 'tries again' and text changed, we may have advanced
        t3 = page.evaluate("document.body.innerText")
        if "tries again" not in t3:
            print(">>> no 'tries again' — advanced or correct!")
            break
    browser.close()
