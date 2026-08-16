#!/usr/bin/env python3
"""Explore the 'Whatever's Needed' playable: dump state, clickables, and screenshots."""
import json, sys, time
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")

from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(2)
    print("TITLE:", page.title())
    print("URL:", page.url)
    print("--- innerText (first 3000 chars) ---")
    txt = page.evaluate("document.body.innerText")
    print(txt[:3000])
    print("--- clickables ---")
    els = page.evaluate("""
        Array.from(document.querySelectorAll('button, a, [role=button], canvas, [onclick], input, [class*=btn], [class*=click], [class*=choice], [class*=option]'))
        .slice(0, 40).map((e, i) => ({i, tag: e.tagName, cls: (e.className||'').toString().slice(0,80), txt: (e.innerText||'').trim().slice(0,60)}))
    """)
    for e in els:
        print(e)
    page.screenshot(path="/tmp/pw_01.png")
    print("screenshot saved /tmp/pw_01.png")
    browser.close()
