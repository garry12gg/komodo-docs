#!/usr/bin/env python3
"""Solve 'Whatever's Needed': for each traveler, try buttons until correct; log the sequence."""
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
    time.sleep(1.0)

    log = []
    for traveler in range(6):
        txt = page.evaluate("document.body.innerText")
        # current speaker + line
        m = re.search(r"([A-Z][A-Z ]*)\n([^\n]{10,})", txt)
        btns = page.evaluate("""
            Array.from(document.querySelectorAll('button')).filter(e => !!(e.offsetWidth||e.offsetHeight)).map(e => (e.innerText||'').trim())
        """)
        # skip the Light the lamp button
        btns = [b for b in btns if b.lower() != "light the lamp"]
        print(f"--- traveler {traveler} | speaker/line: {m.groups() if m else None} | buttons: {btns}")
        if not btns:
            print("NO BUTTONS — end reached?")
            print(txt[-400:])
            break
        solved = False
        for b in btns:
            try:
                page.click(f"button:has-text('{b}')", timeout=4000)
            except Exception:
                continue
            time.sleep(1.3)
            t2 = page.evaluate("document.body.innerText")
            if "tries again" not in t2 and "Not that one" not in t2:
                print(f"  -> {b!r} was CORRECT")
                log.append((m.groups() if m else None, b))
                solved = True
                # wait for the scene to settle / next traveler
                time.sleep(1.5)
                page.screenshot(path=f"/tmp/solve_t{traveler}.png")
                break
            else:
                print(f"  -> {b!r} wrong")
                time.sleep(0.6)
        if not solved:
            print("!! nothing worked this round")
            break
        # check end
        t3 = page.evaluate("document.body.innerText")
        if "made by Scorchio" in t3 and "Light the lamp" not in t3:
            print("END STATE REACHED")
            print(t3[-500:])
            page.screenshot(path="/tmp/solve_end.png")
            break

    print("\n=== SOLUTION LOG ===")
    for i, (who, choice) in enumerate(log):
        print(f"{i+1}. {who} -> {choice}")
    browser.close()
