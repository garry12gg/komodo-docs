#!/usr/bin/env python3
"""Record a playthrough of 'Whatever's Needed' via CDP screencast → JPEG frames.

Dynamic solver: read dialogue, pick correct answer by keyword; first traveler gets
one charming wrong attempt first.
"""
import sys, os, time, base64, re
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
FPS = 15
W, H = 1280, 720

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

def answer_for(text):
    low = text.lower()
    if "stream" in low or "wings" in low or "carry across" in low: return "bridge"
    if "dark" in low or "can't see" in low or "find the door" in low: return "lantern"
    if "lock" in low or "lost the key" in low: return "key"
    if "wall" in low or "grip" in low or "climb" in low: return "ladder"
    if "went out" in low or "cold" in low or "forgot how to start" in low: return "flame"
    return None

def visible_buttons(page):
    return page.evaluate("""
        Array.from(document.querySelectorAll('button')).map((e,i)=>({i, txt:(e.innerText||'').trim(), vis:!!(e.offsetWidth||e.offsetHeight)})).filter(b=>b.vis)
    """)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    cdp = page.context.new_cdp_session(page)

    frame_count = 0
    t0 = time.time()
    next_slot = 0.0

    def on_frame(params):
        global frame_count, next_slot
        meta = params.get("metadata", {})
        ts = meta.get("timestamp", time.time() * 1000) / 1000.0
        if ts >= next_slot:
            next_slot = ts + 1.0 / FPS
            data = base64.b64decode(params["data"])
            frame_count += 1
            with open(f"{OUT}/f{frame_count:05d}.jpg", "wb") as fh:
                fh.write(data)
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 82, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})

    page.goto(URL, wait_until="networkidle", timeout=60000)
    time.sleep(4.5)          # title hold
    page.click("button.btn", timeout=5000)
    time.sleep(2.5)

    for traveler in range(5):
        # wait for choices to appear (settle)
        btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        while not btns:
            time.sleep(0.5)
            btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        txt = page.evaluate("document.body.innerText")
        correct = answer_for(txt)
        print(f"[t{traveler}] correct={correct} choices={[b['txt'] for b in btns]}")
        time.sleep(2.8)      # let dialogue breathe on screen

        if correct is None:
            print("  !! could not determine answer; picking first")
            correct = btns[0]["txt"]

        def click_btn(name):
            bs = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
            t = next((b for b in bs if b["txt"].lower() == name), None)
            if t is None:
                print(f"  !! {name} not among {[b['txt'] for b in bs]}")
                return False
            page.evaluate(f"document.querySelectorAll('button')[{t['i']}].click()")
            return True

        if traveler == 0:
            # one charming wrong attempt
            decoy = next((b["txt"] for b in btns if b["txt"].lower() != correct.lower()), None)
            if decoy:
                click_btn(decoy)
                time.sleep(2.4)   # feedback "Not that one. The tail tries again."
        click_btn(correct)
        time.sleep(3.2)           # resolve + next traveler transition

    # ending: hold
    print("solving done, holding ending...")
    for _ in range(4):
        time.sleep(2.0)

    cdp.send("Page.stopScreencast")
    time.sleep(0.5)
    page.screenshot(path="/tmp/rec_last.png")
    browser.close()

print(f"TOTAL FRAMES: {frame_count}")
