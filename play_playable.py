#!/usr/bin/env python3
"""Play through 'Whatever's Needed': click through choices, capture states."""
import sys, time
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")

from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"

def dump(page, tag):
    txt = page.evaluate("document.body.innerText").strip()
    print(f"=== {tag} | len={len(txt)} ===")
    print(txt[:1200])
    btns = page.evaluate("""
        Array.from(document.querySelectorAll('button, [role=button], [class*=btn]')).map((e,i)=>({i, txt:(e.innerText||'').trim().slice(0,50), vis: !!(e.offsetWidth||e.offsetHeight)}))
    """)
    print("buttons:", btns)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(1.5)
    dump(page, "start")
    page.screenshot(path="/tmp/pw_start.png")
    # click Light the lamp
    page.click("button.btn", timeout=5000)
    time.sleep(1.5)
    dump(page, "after-light")
    page.screenshot(path="/tmp/pw_02.png")
    # keep clicking whatever button appears, up to N steps, screenshot each
    for step in range(20):
        btns = page.evaluate("""
            Array.from(document.querySelectorAll('button, [role=button], [class*=btn]')).filter(e => !!(e.offsetWidth||e.offsetHeight)).map((e,i)=>({i, txt:(e.innerText||'').trim().slice(0,60)}))
        """)
        if not btns:
            print(f"--- no buttons at step {step}; waiting 2s ---")
            time.sleep(2)
            btns = page.evaluate("""
                Array.from(document.querySelectorAll('button, [role=button], [class*=btn]')).filter(e => !!(e.offsetWidth||e.offsetHeight)).map((e,i)=>({i, txt:(e.innerText||'').trim().slice(0,60)}))
            """)
            if not btns:
                break
        print(f"--- step {step}: clicking {btns[0]} ---")
        try:
            page.click(f"button:has-text('{btns[0]['txt'][:20]}')", timeout=4000)
        except Exception as e:
            try:
                page.click("button.btn, [role=button], button", timeout=4000)
            except Exception as e2:
                print("click fail:", e2)
                break
        time.sleep(1.2)
        page.screenshot(path=f"/tmp/pw_step{step:02d}.png")
        txt = page.evaluate("document.body.innerText").strip()
        print(f"step {step} text len={len(txt)} | tail: {txt[-200:]!r}")
        # stop if we reach an end state
        if any(w in txt.lower() for w in ["the end", "thank you", "five warm", "made by scorchio", "door stays open"]):
            print("--- reached end-ish state ---")
            break
    browser.close()
