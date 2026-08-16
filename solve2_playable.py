#!/usr/bin/env python3
"""Solve 'Whatever's Needed' properly: JS clicks, long settles, log correct answers."""
import sys, time, re
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"

def visible_buttons(page):
    return page.evaluate("""
        Array.from(document.querySelectorAll('button')).map((e,i)=>({i, txt:(e.innerText||'').trim(), vis:!!(e.offsetWidth||e.offsetHeight)})).filter(b=>b.vis)
    """)

def speak(page):
    txt = page.evaluate("document.body.innerText")
    m = re.search(r"([A-Z][A-Z ]{1,12})\n([^\n]{8,})", txt)
    return (m.groups() if m else None), txt

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(1.5)
    page.click("button.btn", timeout=5000)
    time.sleep(2.5)

    log = []
    for traveler in range(6):
        (who, line), txt = speak(page)
        btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        print(f"--- traveler {traveler}: {who}: {line[:70]!r} | choices: {[b['txt'] for b in btns]}")
        if not btns:
            print("NO CHOICE BUTTONS — check end state")
            print(txt[-600:])
            break
        solved = False
        for b in btns:
            page.evaluate(f"document.querySelectorAll('button')[{b['i']}].click()")
            # poll for text change up to 4s
            t0 = time.time(); changed = None
            while time.time() - t0 < 4.0:
                time.sleep(0.4)
                t2 = page.evaluate("document.body.innerText")
                if t2 != txt:
                    changed = t2
                    break
            if changed is None:
                print(f"  {b['txt']!r}: no change??")
                continue
            if "tries again" in changed or "Not that one" in changed:
                print(f"  {b['txt']!r}: WRONG")
                time.sleep(0.8)
                txt = page.evaluate("document.body.innerText")  # reset baseline
            else:
                print(f"  {b['txt']!r}: CORRECT")
                log.append((who, b["txt"]))
                solved = True
                time.sleep(2.5)
                page.screenshot(path=f"/tmp/solve2_t{traveler}.png")
                break
        if not solved:
            print("!! stuck at traveler", traveler)
            break
        t3 = page.evaluate("document.body.innerText")
        if "Light the lamp" not in t3 and "made by Scorchio" in t3:
            print("END STATE")
            page.screenshot(path="/tmp/solve2_end.png")
            print(t3[-600:])
            break

    print("\n=== SOLUTION ===")
    for i, (who, choice) in enumerate(log):
        print(f"{i+1}. {who} -> {choice}")
    browser.close()
